import os
import time
import uuid
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from azure.data.tables import TableClient
from brain import evaluate_job

# 1. Pull secure details from Azure Environment Variables
# We set fallbacks here just in case the env vars don't load perfectly
CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vamshi Krishna Boddu")
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "vamshikrishna852@gmail.com")
CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE", "989-954-2212")
STORAGE_CONN_STR = os.getenv("STORAGE_CONN_STR")
RESUME_PATH = "/app/resume.pdf"

# 2. Initialize Azure Database Connection
table_client = None
if STORAGE_CONN_STR:
    try:
        table_client = TableClient.from_connection_string(conn_str=STORAGE_CONN_STR, table_name="AppliedJobs")
        print("Successfully connected to Azure Table Storage.")
    except Exception as e:
        print(f"Warning: Could not connect to Azure Table Storage. Error: {e}")
else:
    print("Warning: STORAGE_CONN_STR environment variable is missing.")

def log_application(url, title, description):
    """Parses the page title and saves the record to Azure Table Storage"""
    if not table_client:
        return
        
    try:
        # Dice titles usually format as "Role - Company - Location | Dice.com"
        parts = title.replace('| Dice.com', '').split(' - ')
        job_role = parts[0].strip() if len(parts) > 0 else "Unknown Role"
        company = parts[1].strip() if len(parts) > 1 else "Unknown Company"
        location = parts[2].strip() if len(parts) > 2 else "Unknown Location"
        
        # Max Azure Table string length is 32k, so we truncate the description
        safe_desc = description[:30000] if description else "No description extracted"

        entity = {
            "PartitionKey": "Dice",
            "RowKey": str(uuid.uuid4()), # Generates a unique ID for the log entry
            "JobUrl": url,
            "JobRole": job_role,
            "Company": company,
            "Location": location,
            "Description": safe_desc,
            "DateApplied": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        table_client.create_entity(entity=entity)
        print(f"--> Successfully logged {job_role} at {company} to Azure DB.")
    except Exception as e:
        print(f"Failed to log to database: {e}")

def apply_on_dice(page):
    print("--- Starting Dice Job Search ---")
    
    # 3. The Search Queues: Dallas (On-Site/Hybrid) and Remote (Anywhere)
    search_urls = [
        'https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&location=Dallas,+TX&radius=30&radiusUnit=mi&filters.easyApply=true&filters.workplaceTypes=On-Site%7CHybrid',
        'https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&filters.easyApply=true&filters.workplaceTypes=Remote'
    ]

    for search_url in search_urls:
        print(f"\n--- Scraping Queue: {search_url} ---")
        page.goto(search_url)
        
        try:
            # Wait for the search results to finish loading
            page.wait_for_load_state('networkidle', timeout=30000)
            time.sleep(3) 
            
            # Extract job links
            job_links = page.locator('a.card-title-link').all()
            if len(job_links) == 0:
                print("Standard link class not found. Trying fallback URL selector...")
                job_links = page.locator('a[href*="/job-detail/"]').all()
                
            print(f"Found {len(job_links)} jobs in this queue.")

            # Grab all the raw URLs
            job_urls = []
            for link in job_links:
                href = link.get_attribute('href')
                if href:
                    if href.startswith('/'): 
                        href = f"https://www.dice.com{href}"
                    job_urls.append(href)

            # 4. Visit each job directly and apply
            for url in job_urls:
                print(f"\nNavigating to job: {url}")
                page.goto(url)
                
                try:
                    # FIX 1: Bypass the infinite tracker trap by using domcontentloaded instead of networkidle
                    page.wait_for_load_state('domcontentloaded', timeout=15000)
                    time.sleep(2) 
                    
                    # Extract the text
                    try:
                        description_text = page.locator('#jobdescSec, .job-description, [data-cy="job-description"]').first.inner_text(timeout=5000)
                    except:
                        print("Standard description tags not found. Brute-forcing page text...")
                        description_text = page.locator('body').inner_text()
                        
                    print("Extracted description. Sending to OpenAI for evaluation...")
                    
                    is_match = evaluate_job(description_text)
                    
                    if is_match:
                        print("OpenAI approved! Initiating application sequence...")
                        
                        try:
                            # 1. Click the Apply Button
                            print("-> Looking for the Apply button...")
                            apply_button = page.locator('button:has-text("Apply"), a:has-text("Apply")').first
                            apply_button.click(timeout=10000)
                            
                            # Give the modal/popup a generous moment to render
                            time.sleep(4)
                            
                            # 2. Fill First and Last Name
                            print("-> Filling candidate name...")
                            name_parts = CANDIDATE_NAME.split()
                            first_name = name_parts[0]
                            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            
                            # Broadened selectors to catch shadow DOMs or weird IDs
                            page.locator('input[name*="first"], input[placeholder*="First"]').first.fill(first_name, timeout=5000)
                            page.locator('input[name*="last"], input[placeholder*="Last"]').first.fill(last_name, timeout=5000)
                            
                            # 3. Fill Email
                            print("-> Filling email...")
                            page.locator('input[type="email"], input[name*="email"]').first.fill(CANDIDATE_EMAIL, timeout=5000)
                            
                            # 4. Fill Phone
                            if page.locator('input[type="tel"], input[name*="phone"]').first.is_visible():
                                print("-> Filling phone number...")
                                page.locator('input[type="tel"], input[name*="phone"]').first.fill(CANDIDATE_PHONE)
                                
                            # 5. Upload Resume
                            print("-> Uploading resume...")
                            page.locator('input[type="file"]').first.set_input_files(RESUME_PATH, timeout=5000)
                            
                            # 6. Submit Application
                            print("-> Submitting application...")
                            page.locator('button:has-text("Submit"), button:has-text("Next"), button:has-text("Send")').first.click(timeout=5000)
                            print("✅ Application submitted successfully!")
                            
                            log_application(url, page.title(), description_text)
                            
                        except Exception as apply_err:
                            print(f"❌ Application step failed! The bot got stuck on the form.")
                            print(f"Exact Form Error: {apply_err}")
                            
                            # FIX 2: Bot Vision - Dump the screen text so we can see what blocked it
                            print("\n--- 🤖 WHAT THE BOT SEES RIGHT NOW ---")
                            print(f"Current URL: {page.url}")
                            try:
                                visible_text = page.locator("body").inner_text()
                                print(f"Screen Text:\n{visible_text[:800]}...\n--------------------------------------")
                            except:
                                print("Could not scrape screen text.")
                            
                    else:
                        print("OpenAI rejected this role. Skipping.")
                
                except Exception as inner_e:
                    print(f"Failed to process individual job. Skipping. Error: {inner_e}")
                    
        except Exception as e:
            print(f"Queue timeout/error. Title: '{page.title()}' | Error: {e}")

def run_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Apply stealth to bypass bot protection
        stealth_sync(page) 
        
        apply_on_dice(page)
        
        browser.close()
        print("\n--- Daily Job Hunt Complete ---")

if __name__ == "__main__":
    run_scraper()