import os
import time
import uuid
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from azure.data.tables import TableClient
from brain import evaluate_job

CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vamshi Krishna Boddu")
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "vamshikrishna852@gmail.com")
CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE", "989-954-2212")
STORAGE_CONN_STR = os.getenv("STORAGE_CONN_STR")

DICE_USERNAME = os.getenv("DICE_USERNAME") 
DICE_PASSWORD = os.getenv("DICE_PASSWORD") 

RESUME_PATH = "/app/resume.pdf"

table_client = None
if STORAGE_CONN_STR:
    try:
        table_client = TableClient.from_connection_string(conn_str=STORAGE_CONN_STR, table_name="AppliedJobs")
        print("Successfully connected to Azure Table Storage.")
    except Exception as e:
        print(f"Warning: Could not connect to Azure Table Storage. Error: {e}")

def log_application(url, job_role, company, description, status):
    if not table_client:
        return
    try:
        safe_desc = description[:30000] if description else "No description extracted"
        if not job_role: job_role = "Unknown Role"
        if not company: company = "Unknown Company"

        entity = {
            "PartitionKey": "Dice",
            "RowKey": str(uuid.uuid4()),
            "JobUrl": url,
            "JobRole": job_role,
            "Company": company,
            "Location": "Remote/Dallas",
            "Description": safe_desc,
            "Status": status, 
            "DateLogged": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        table_client.create_entity(entity=entity)
        print(f"--> Logged to DB: [{status}] | {job_role} at {company}")
    except Exception as e:
        print(f"Failed to log to database: {e}")

def login_to_dice(page):
    if not DICE_USERNAME or not DICE_PASSWORD:
        print("⚠️ Warning: No credentials found. Bot will attempt to apply as a guest.")
        return

    print("\n--- 🔐 Authenticating with Dice ---")
    page.goto('https://www.dice.com/dashboard/login')
    
    try:
        page.wait_for_load_state('domcontentloaded')
        time.sleep(3)
        
        page.locator('input[type="email"]:visible, input[name="email"]:visible').first.fill(DICE_USERNAME, timeout=10000)
        
        next_btn = page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible').first
        if next_btn.is_visible():
            next_btn.click()
            time.sleep(2)
            
        page.locator('input[type="password"]:visible, input[name="password"]:visible').first.fill(DICE_PASSWORD, timeout=10000)
        page.locator('button:has-text("Sign In"):visible, button[type="submit"]:visible').first.click()
        
        time.sleep(5)
        print("✅ Successfully logged in!")
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
        try:
            page.goto(search_url)
            page.wait_for_load_state('domcontentloaded', timeout=30000)
            time.sleep(3) 
            
            job_links = page.locator('a.card-title-link').all()
            if len(job_links) == 0:
                job_links = page.locator('a[href*="/job-detail/"]').all()
                
            job_urls = []
            for link in job_links:
                href = link.get_attribute('href')
                if href:
                    href = href.split('?')[0]
                    if href.startswith('/'): 
                        href = f"https://www.dice.com{href}"
                    job_urls.append(href)

            # Deduplicate the URLs to save OpenAI API Tokens
            job_urls = list(dict.fromkeys(job_urls))
            print(f"Found {len(job_urls)} UNIQUE jobs in this queue.")

            for url in job_urls:
                print(f"\nNavigating to job: {url}")
                try:
                    page.goto(url)
                    page.wait_for_load_state('domcontentloaded', timeout=15000)
                    time.sleep(2) 
                    
                    try:
                        job_role = page.locator('h1.jobTitle, h1[data-cy="jobTitle"]').first.inner_text(timeout=3000)
                        company = page.locator('a[data-cy="companyNameLink"]').first.inner_text(timeout=3000)
                    except:
                        parts = page.title().replace('| Dice.com', '').split(' - ')
                        job_role = parts[0].strip() if len(parts) > 0 else "Unknown Role"
                        company = parts[1].strip() if len(parts) > 1 else "Unknown Company"

                    try:
                        description_text = page.locator('#jobdescSec, .job-description, [data-cy="job-description"]').first.inner_text(timeout=5000)
                    except:
                        description_text = page.locator('body').inner_text()
                        
                    print("Extracted description. Sending to OpenAI for evaluation...")
                    is_match = evaluate_job(description_text)
                    
                    if is_match:
                        print("OpenAI approved! Initiating application sequence...")
                        
                        try:
                            # 1. Check if already applied
                            is_applied = page.evaluate('''() => {
                                const wc = document.querySelector('apply-button-wc');
                                return (wc && wc.getAttribute('status') === 'applied') || document.body.innerText.includes('Already Applied');
                            }''')
                            
                            if is_applied:
                                print("-> ⚠️ Already applied to this job! Skipping.")
                                log_application(url, job_role, company, description_text, "Already Applied")
                                continue

                            # 2. JavaScript Click Injection (Bypasses UI Locks)
                            print("-> Clicking Apply Button via JS...")
                            page.evaluate('''() => {
                                const wc = document.querySelector('apply-button-wc');
                                if (wc && wc.shadowRoot) {
                                    const btn = wc.shadowRoot.querySelector('button');
                                    if (btn) btn.click();
                                } else {
                                    const btns = Array.from(document.querySelectorAll('button'));
                                    const applyBtn = btns.find(b => b.innerText.includes('Apply'));
                                    if (applyBtn) applyBtn.click();
                                }
                            }''')
                            time.sleep(4)
                            
                            # 3. Smart Form Filler
                            try:
                                first_name_input = page.locator('input[name*="first"]:visible, input[placeholder*="First"]:visible').first
                                if first_name_input.is_visible(timeout=3000):
                                    print("-> Filling empty contact fields...")
                                    name_parts = CANDIDATE_NAME.split()
                                    first_name = name_parts[0]
                                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                                    first_name_input.fill(first_name, force=True)
                                    page.locator('input[name*="last"]:visible, input[placeholder*="Last"]:visible').first.fill(last_name, force=True)
                                    page.locator('input[type="email"]:visible, input[name*="email"]:visible').first.fill(CANDIDATE_EMAIL, force=True)
                                else:
                                    print("-> Contact info already pre-filled by Dice Profile!")
                            except:
                                print("-> Skipping contact fields (Not found or already pre-filled).")

                            try:
                                phone_input = page.locator('input[type="tel"]:visible, input[name*="phone"]:visible').first
                                if phone_input.is_visible(timeout=2000) and not phone_input.input_value():
                                    phone_input.fill(CANDIDATE_PHONE, force=True)
                            except:
                                pass

                            # 4. Click through the "Next" wizard
                            for i in range(5):
                                try:
                                    next_btn = page.locator('button:has-text("Next"):visible, button:has-text("Continue"):visible').first
                                    if next_btn.is_visible(timeout=1000):
                                        print(f"-> Clicking Next (Step {i+1})...")
                                        next_btn.click(force=True)
                                        time.sleep(2)
                                except:
                                    break

                            # 5. Submit Application
                            print("-> Submitting application...")
                            submit_btn = page.locator('button:has-text("Submit Application"):visible, button:has-text("Submit"):visible, button:has-text("Finish"):visible, button:has-text("Send"):visible').first
                            submit_btn.click(timeout=5000, force=True)
                            print("✅ Application submitted successfully!")
                            
                            log_application(url, job_role, company, description_text, "Approved & Applied")
                            
                        except Exception as apply_err:
                            print(f"❌ Application step failed! Exact Form Error: {apply_err}")
                            log_application(url, job_role, company, description_text, "Approved but Failed")
                            
                    else:
                        print("OpenAI rejected this role. Skipping.")
                        log_application(url, job_role, company, description_text, "Rejected by AI")
                
                except Exception as inner_e:
                    print(f"Failed to process individual job. Skipping. Error: {inner_e}")
                    
        except Exception as e:
            print(f"Queue error. | Error: {e}")

def run_scraper():
    with sync_playwright() as p:
        # FIX 1: Add --disable-dev-shm-usage to prevent the container from crashing
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context()
        page = context.new_page()
        
        stealth_sync(page) 
        login_to_dice(page)
        apply_on_dice(page)
        
        browser.close()
        print("\n--- Daily Job Hunt Complete ---")

if __name__ == "__main__":
    run_scraper()