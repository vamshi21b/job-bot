import os
import time
import uuid
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from azure.data.tables import TableClient
from brain import evaluate_job

# 1. Pull secure details from Azure Environment Variables
CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vamshi Krishna Boddu")
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "vamshikrishna852@gmail.com")
CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE", "989-954-2212")
STORAGE_CONN_STR = os.getenv("STORAGE_CONN_STR")

# Dice Credentials
DICE_USERNAME = os.getenv("DICE_USERNAME") 
DICE_PASSWORD = os.getenv("DICE_PASSWORD") 

RESUME_PATH = "/app/resume.pdf"

# 2. Initialize Azure Database Connection
table_client = None
if STORAGE_CONN_STR:
    try:
        table_client = TableClient.from_connection_string(conn_str=STORAGE_CONN_STR, table_name="AppliedJobs")
        print("Successfully connected to Azure Table Storage.")
    except Exception as e:
        print(f"Warning: Could not connect to Azure Table Storage. Error: {e}")

def log_application(url, title, description, status):
    """Parses the page title and saves the record to Azure Table Storage with Status"""
    if not table_client:
        return
        
    try:
        parts = title.replace('| Dice.com', '').split(' - ')
        job_role = parts[0].strip() if len(parts) > 0 else "Unknown Role"
        company = parts[1].strip() if len(parts) > 1 else "Unknown Company"
        location = parts[2].strip() if len(parts) > 2 else "Unknown Location"
        
        safe_desc = description[:30000] if description else "No description extracted"

        entity = {
            "PartitionKey": "Dice",
            "RowKey": str(uuid.uuid4()),
            "JobUrl": url,
            "JobRole": job_role,
            "Company": company,
            "Location": location,
            "Description": safe_desc,
            "Status": status, # <--- NEW STATUS FIELD
            "DateLogged": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        table_client.create_entity(entity=entity)
        print(f"--> Logged to DB: [{status}] | {job_role} at {company}")
    except Exception as e:
        print(f"Failed to log to database: {e}")

def login_to_dice(page):
    """Authenticates the bot to bypass the Dice login wall"""
    if not DICE_USERNAME or not DICE_PASSWORD:
        print("⚠️ Warning: No DICE_USERNAME or DICE_PASSWORD found. Bot will attempt to apply as a guest.")
        return

    print("\n--- 🔐 Authenticating with Dice ---")
    page.goto('https://www.dice.com/dashboard/login')
    
    try:
        page.wait_for_load_state('domcontentloaded')
        time.sleep(3)
        
        print("-> Entering email...")
        page.locator('input[type="email"], input[name="email"]').first.fill(DICE_USERNAME, timeout=10000)
        
        next_btn = page.locator('button:has-text("Continue"), button:has-text("Next")').first
        if next_btn.is_visible():
            next_btn.click()
            time.sleep(2)
            
        print("-> Entering password...")
        page.locator('input[type="password"], input[name="password"]').first.fill(DICE_PASSWORD, timeout=10000)
        
        print("-> Clicking Sign In...")
        page.locator('button:has-text("Sign In"), button[type="submit"]').first.click()
        
        time.sleep(5)
        print("✅ Successfully logged in! The login wall is now bypassed.")
    except Exception as e:
        print(f"❌ Failed to log in. Error: {e}")

def apply_on_dice(page):
    print("--- Starting Dice Job Search ---")
    
    search_urls = [
        'https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&location=Dallas,+TX&radius=30&radiusUnit=mi&filters.easyApply=true&filters.workplaceTypes=On-Site%7CHybrid',
        'https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&filters.easyApply=true&filters.workplaceTypes=Remote'
    ]

    for search_url in search_urls:
        print(f"\n--- Scraping Queue: {search_url} ---")
        page.goto(search_url)
        
        try:
            page.wait_for_load_state('domcontentloaded', timeout=30000)
            time.sleep(3) 
            
            job_links = page.locator('a.card-title-link').all()
            if len(job_links) == 0:
                job_links = page.locator('a[href*="/job-detail/"]').all()
                
            print(f"Found {len(job_links)} jobs in this queue.")

            job_urls = []
            for link in job_links:
                href = link.get_attribute('href')
                if href:
                    if href.startswith('/'): 
                        href = f"https://www.dice.com{href}"
                    job_urls.append(href)

            for url in job_urls:
                print(f"\nNavigating to job: {url}")
                page.goto(url)
                
                try:
                    page.wait_for_load_state('domcontentloaded', timeout=15000)
                    time.sleep(2) 
                    
                    try:
                        description_text = page.locator('#jobdescSec, .job-description, [data-cy="job-description"]').first.inner_text(timeout=5000)
                    except:
                        description_text = page.locator('body').inner_text()
                        
                    print("Extracted description. Sending to OpenAI for evaluation...")
                    is_match = evaluate_job(description_text)
                    
                    if is_match:
                        print("OpenAI approved! Initiating application sequence...")
                        
                        try:
                            # FIX 1: The Cascading Shadow DOM Locator
                            print("-> Looking for the Apply button...")
                            
                            # We use a broad CSS selector that natively pierces Shadow DOMs in modern Playwright
                            apply_button = page.locator('apply-button-wc button, button:has-text("Apply"), a:has-text("Apply")').first
                            apply_button.click(timeout=10000)
                            time.sleep(4)
                            
                            # 2. Smart Form Filler
                            first_name_input = page.locator('input[name*="first"], input[placeholder*="First"]').first
                            try:
                                if first_name_input.is_visible(timeout=3000):
                                    print("-> Filling empty contact fields...")
                                    name_parts = CANDIDATE_NAME.split()
                                    first_name = name_parts[0]
                                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                                    first_name_input.fill(first_name)
                                    page.locator('input[name*="last"], input[placeholder*="Last"]').first.fill(last_name)
                                    page.locator('input[type="email"], input[name*="email"]').first.fill(CANDIDATE_EMAIL)
                            except:
                                print("-> Contact info already pre-filled by Dice Profile!")

                            # 3. Phone Number 
                            try:
                                phone_input = page.locator('input[type="tel"], input[name*="phone"]').first
                                if phone_input.is_visible(timeout=2000) and not phone_input.input_value():
                                    print("-> Filling phone number...")
                                    phone_input.fill(CANDIDATE_PHONE)
                            except:
                                pass

                            # 4. Click through the "Next" wizard for complex forms
                            for i in range(3):
                                try:
                                    next_btn = page.locator('button:has-text("Next")').first
                                    if next_btn.is_visible(timeout=1000):
                                        print(f"-> Clicking Next (Step {i+1})...")
                                        next_btn.click()
                                        time.sleep(2)
                                except:
                                    break

                            # 5. Submit Application
                            print("-> Submitting application...")
                            submit_btn = page.locator('button:has-text("Submit"), button:has-text("Send")').first
                            submit_btn.click(timeout=5000)
                            print("✅ Application submitted successfully!")
                            
                            # Log as Successful Apply
                            log_application(url, page.title(), description_text, "Approved & Applied")
                            
                        except Exception as apply_err:
                            print(f"❌ Application step failed! Exact Form Error: {apply_err}")
                            # Log as Failed Apply
                            log_application(url, page.title(), description_text, "Approved but Failed")
                            
                    else:
                        print("OpenAI rejected this role. Skipping.")
                        # Log as Rejected
                        log_application(url, page.title(), description_text, "Rejected by AI")
                
                except Exception as inner_e:
                    print(f"Failed to process individual job. Skipping. Error: {inner_e}")
                    
        except Exception as e:
            print(f"Queue error. | Error: {e}")

def run_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        stealth_sync(page) 
        login_to_dice(page)
        apply_on_dice(page)
        
        browser.close()
        print("\n--- Daily Job Hunt Complete ---")

if __name__ == "__main__":
    run_scraper()