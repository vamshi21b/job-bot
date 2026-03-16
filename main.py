import os
import time
import uuid
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from azure.data.tables import TableClient
from brain import evaluate_job

# 1. Pull secure details
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
        print(f"Warning: Could not connect to Azure DB. Error: {e}")

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

def universal_click(page, keywords, timeout=5):
    """Searches the main page AND all cross-origin iframes for specific buttons"""
    start = time.time()
    while time.time() - start < timeout:
        # Iterate over every single iframe loaded on the page
        for frame in page.frames:
            try:
                clicked = frame.evaluate('''([keywords]) => {
                    function pierce(root) {
                        let found = null;
                        const els = root.querySelectorAll('*');
                        for (let el of els) {
                            if (el.shadowRoot) {
                                let res = pierce(el.shadowRoot);
                                if (res) found = res;
                            }
                            if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button') {
                                const txt = (el.innerText || el.value || '').toLowerCase().trim();
                                for (let k of keywords) {
                                    if (txt === k || (k !== 'submit' && txt.includes(k))) {
                                        const rect = el.getBoundingClientRect();
                                        // Ensure the button is actually physically visible on the screen
                                        if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden') {
                                            found = el;
                                            break;
                                        }
                                    }
                                }
                            }
                            if (found) break;
                        }
                        return found;
                    }
                    const btn = pierce(document);
                    if (btn) {
                        // Dispatch a true hardware mouse event
                        btn.dispatchEvent(new PointerEvent('click', { view: window, bubbles: true, cancelable: true, buttons: 1 }));
                        return true;
                    }
                    return false;
                }''', [keywords])
                if clicked:
                    return True
            except:
                continue
        time.sleep(1)
    return False

def check_success(page):
    """Scans all iframes for success confirmation text"""
    for frame in page.frames:
        try:
            success = frame.evaluate('''() => {
                const text = document.body.innerText.toLowerCase();
                return text.includes('application was sent') || 
                       text.includes('application submitted') || 
                       text.includes('successfully applied') ||
                       text.includes('applied successfully') ||
                       text.includes('received your application');
            }''')
            if success:
                return True
        except:
            continue
            
    # Check if the main apply button changed to "Applied"
    try:
        status = page.evaluate("() => { const wc = document.querySelector('apply-button-wc'); return wc ? wc.getAttribute('status') : null; }")
        if status == 'applied':
            return True
    except:
        pass
        
    return False

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

                            # 2. Open Modal via JS Injection
                            print("-> Clicking Apply Button to open modal...")
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
                            
                            # Give modal PLENTY of time to load and inject iframes
                            time.sleep(5) 
                            
                            # 3. Form Loop (Next / Submit)
                            # We will loop up to 6 times using the new iframe-aware universal_click function
                            submitted = False
                            for step in range(6):
                                print(f"-> Form Step {step+1}...")
                                
                                # First, try to find and click submit/finish
                                if universal_click(page, ['submit application', 'submit', 'finish application', 'finish', 'send'], timeout=3):
                                    print("-> Clicked Submit button!")
                                    submitted = True
                                    time.sleep(4)
                                    break
                                
                                # If no submit button, look for next/continue
                                elif universal_click(page, ['next', 'continue'], timeout=3):
                                    print("-> Clicked Next/Continue button.")
                                    time.sleep(3) # Wait for next page of the iframe to load
                                    
                                else:
                                    print("-> Could not find Next or Submit button on this screen.")
                                    # Fallback: Just look for any primary button inside the iframe
                                    if universal_click(page, ['apply'], timeout=2):
                                        print("-> Clicked a generic 'Apply' button.")
                                        time.sleep(3)
                                    else:
                                        print("-> Stuck on form. Breaking loop.")
                                        break
                                        
                            if not submitted:
                                print("-> Warning: Reached end of loop without explicitly clicking 'Submit'.")
                                
                            # 4. Verify success across all iframes
                            if check_success(page):
                                print("✅ Application verified and submitted successfully!")
                                log_application(url, job_role, company, description_text, "Approved & Applied")
                            else:
                                print("❌ Success screen not detected. Form may have failed or required manual input.")
                                log_application(url, job_role, company, description_text, "Approved but Failed")
                            
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