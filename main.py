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
    except:
        pass

def log_application(url, job_role, company, description, status):
    if not table_client: return
    try:
        safe_desc = description[:30000] if description else "No desc"
        if not job_role: job_role = "Unknown Role"
        if not company: company = "Unknown Company"
        entity = {
            "PartitionKey": "Dice", "RowKey": str(uuid.uuid4()),
            "JobUrl": url, "JobRole": job_role, "Company": company,
            "Location": "Remote/Dallas", "Description": safe_desc,
            "Status": status, "DateLogged": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        table_client.create_entity(entity=entity)
        print(f"--> Logged to DB: [{status}] | {job_role} at {company}")
    except:
        pass

def login_to_dice(page):
    if not DICE_USERNAME or not DICE_PASSWORD: return
    print("\n--- 🔐 Authenticating with Dice ---")
    page.goto('https://www.dice.com/dashboard/login')
    try:
        page.wait_for_load_state('domcontentloaded')
        time.sleep(3)
        page.locator('input[type="email"]:visible').first.fill(DICE_USERNAME)
        next_btn = page.locator('button:has-text("Continue"):visible, button:has-text("Next"):visible').first
        if next_btn.is_visible():
            next_btn.click()
            time.sleep(2)
        page.locator('input[type="password"]:visible').first.fill(DICE_PASSWORD)
        page.locator('button:has-text("Sign In"):visible, button[type="submit"]:visible').first.click()
        time.sleep(5)
        print("✅ Successfully logged in!")
    except Exception as e:
        print(f"❌ Failed to log in: {e}")

def solve_custom_questions(page):
    """Auto-fills common HR questions on the screen before clicking Next"""
    for frame in page.frames:
        try:
            frame.evaluate('''() => {
                // 1. Dropdowns: Select the second option (usually the first valid answer after "Select One")
                document.querySelectorAll('select').forEach(s => {
                    if (s.options.length > 1 && s.selectedIndex <= 0) {
                        s.selectedIndex = 1;
                        s.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
                
                // 2. Radio Buttons / Checkboxes: Look for Yes/No
                document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(r => {
                    const textNextToIt = (r.nextElementSibling ? r.nextElementSibling.innerText : '').toLowerCase();
                    const value = r.value.toLowerCase();
                    
                    // We want to click "Yes" for authorization/clearance, "No" for requiring sponsorship
                    if ((textNextToIt.includes('yes') || value.includes('yes')) && !r.checked) {
                        // Avoid answering "Yes" to "Do you need sponsorship?"
                        const parentText = r.parentElement.parentElement.innerText.toLowerCase();
                        if (!parentText.includes('sponsorship') && !parentText.includes('require visa')) {
                            r.click();
                        }
                    } else if ((textNextToIt.includes('no') || value.includes('no')) && !r.checked) {
                        const parentText = r.parentElement.parentElement.innerText.toLowerCase();
                        if (parentText.includes('sponsorship') || parentText.includes('require visa')) {
                            r.click();
                        }
                    }
                });
            }''')
        except:
            continue

def universal_click(page, keywords, timeout=5):
    """Searches the main page AND iframes, ignoring disabled buttons and the background page"""
    start = time.time()
    while time.time() - start < timeout:
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
                            // Anti-Background Click: If a modal is open, ignore the main page buttons
                            if (document.querySelector('seds-modal') && !el.closest('seds-modal') && !window.location.href.includes('iframe')) {
                                continue; 
                            }
                            
                            if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button') {
                                // Ignore disabled buttons
                                if (el.disabled || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('disabled')) continue;
                                
                                const txt = (el.innerText || el.value || '').toLowerCase().trim();
                                for (let k of keywords) {
                                    if (txt === k || (k !== 'submit' && txt.includes(k))) {
                                        const rect = el.getBoundingClientRect();
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
                        btn.dispatchEvent(new PointerEvent('click', { view: window, bubbles: true, cancelable: true, buttons: 1 }));
                        return true;
                    }
                    return false;
                }''', [keywords])
                if clicked: return True
            except:
                continue
        time.sleep(1)
    return False

def check_success(page):
    for frame in page.frames:
        try:
            success = frame.evaluate('''() => {
                const text = document.body.innerText.toLowerCase();
                return text.includes('application was sent') || text.includes('application submitted') || 
                       text.includes('successfully applied') || text.includes('received your application');
            }''')
            if success: return True
        except: continue
    try:
        status = page.evaluate("() => { const wc = document.querySelector('apply-button-wc'); return wc ? wc.getAttribute('status') : null; }")
        if status == 'applied': return True
    except: pass
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
            if not job_links: job_links = page.locator('a[href*="/job-detail/"]').all()
                
            job_urls = list(dict.fromkeys([link.get_attribute('href').split('?')[0] if not link.get_attribute('href').startswith('/') else f"https://www.dice.com{link.get_attribute('href').split('?')[0]}" for link in job_links if link.get_attribute('href')]))
            print(f"Found {len(job_urls)} UNIQUE jobs.")

            for url in job_urls:
                print(f"\nNavigating to job: {url}")
                try:
                    page.goto(url)
                    page.wait_for_load_state('domcontentloaded', timeout=15000)
                    time.sleep(2) 
                    
                    try: job_role = page.locator('h1.jobTitle, h1[data-cy="jobTitle"]').first.inner_text(timeout=3000)
                    except: job_role = page.title().replace('| Dice.com', '').split(' - ')[0].strip()
                    try: company = page.locator('a[data-cy="companyNameLink"]').first.inner_text(timeout=3000)
                    except: company = "Unknown Company"

                    try: description_text = page.locator('#jobdescSec, .job-description').first.inner_text(timeout=5000)
                    except: description_text = page.locator('body').inner_text()
                        
                    is_match = evaluate_job(description_text)
                    if is_match:
                        print("OpenAI approved! Initiating application sequence...")
                        try:
                            is_applied = page.evaluate('''() => {
                                const wc = document.querySelector('apply-button-wc');
                                return (wc && wc.getAttribute('status') === 'applied') || document.body.innerText.includes('Already Applied');
                            }''')
                            if is_applied:
                                print("-> ⚠️ Already applied to this job! Skipping.")
                                log_application(url, job_role, company, description_text, "Already Applied")
                                continue

                            print("-> Clicking Apply Button to open modal...")
                            universal_click(page, ['apply now', 'apply'], timeout=5)
                            time.sleep(5) 
                            
                            submitted = False
                            for step in range(7):
                                print(f"-> Form Step {step+1}...")
                                
                                # RUN THE AI AUTO-SOLVER BEFORE CLICKING ANYTHING
                                solve_custom_questions(page)
                                time.sleep(1)
                                
                                if universal_click(page, ['submit application', 'submit', 'finish application', 'finish', 'send'], timeout=3):
                                    print("-> Clicked Submit button!")
                                    submitted = True
                                    time.sleep(5)
                                    break
                                elif universal_click(page, ['next', 'continue'], timeout=3):
                                    print("-> Clicked Next/Continue button.")
                                    time.sleep(3)
                                else:
                                    print("-> Stuck on form. Could not find Next or Submit button.")
                                    break
                                        
                            if check_success(page):
                                print("✅ Application verified and submitted successfully!")
                                log_application(url, job_role, company, description_text, "Approved & Applied")
                            else:
                                print("❌ Success screen not detected. Form may have failed or required manual input.")
                                log_application(url, job_role, company, description_text, "Approved but Failed")
                            
                        except Exception as apply_err:
                            log_application(url, job_role, company, description_text, "Approved but Failed")
                    else:
                        print("OpenAI rejected this role. Skipping.")
                        log_application(url, job_role, company, description_text, "Rejected by AI")
                except Exception as inner_e:
                    print(f"Skipping. Error: {inner_e}")
        except Exception as e:
            print(f"Queue error: {e}")

def run_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"])
        page = browser.new_context().new_page()
        stealth_sync(page) 
        login_to_dice(page)
        apply_on_dice(page)
        browser.close()

if __name__ == "__main__":
    run_scraper()