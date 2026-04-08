import os
import time
import uuid
import json
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from azure.data.tables import TableClient
from azure.storage.blob import BlobServiceClient
from brain import evaluate_job
from resume_builder import generate_tailored_resume

# --- 1. SECURE CREDENTIALS ---
CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vamshi Krishna Boddu")
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "vamshikrishna852@gmail.com")
CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE", "989-954-2212")
STORAGE_CONN_STR = os.getenv("STORAGE_CONN_STR")

DICE_USERNAME = os.getenv("DICE_USERNAME") 
DICE_PASSWORD = os.getenv("DICE_PASSWORD") 
MONSTER_USERNAME = os.getenv("MONSTER_USERNAME")
MONSTER_PASSWORD = os.getenv("MONSTER_PASSWORD")

# JSON Cookie strings from GitHub Secrets
INDEED_COOKIES = os.getenv("INDEED_COOKIES")
ZIP_COOKIES = os.getenv("ZIP_COOKIES")

RESUME_PATH = "/app/resume.pdf" 

# --- 2. AZURE CONNECTIONS ---
table_client = None
blob_service_client = None

if STORAGE_CONN_STR:
    try:
        table_client = TableClient.from_connection_string(conn_str=STORAGE_CONN_STR, table_name="AppliedJobs")
        blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
        container_client = blob_service_client.get_container_client("resumes")
        if not container_client.exists():
            try: container_client.create_container()
            except Exception as ce: print(f"Failed to create resumes container: {ce}")
        print("Successfully connected to Azure Table and Blob Storage.")
    except Exception as e:
        print(f"Warning: Could not connect to Azure Storage. Error: {e}")

def get_previously_applied_jobs():
    applied_urls = set()
    if table_client:
        try:
            print("-> Fetching historical application data from Azure to prevent duplicates...")
            for entity in table_client.list_entities():
                url = entity.get("JobUrl")
                if url: applied_urls.add(url.split('?')[0])
            print(f"-> Found {len(applied_urls)} previously processed jobs.")
        except Exception as e: print(f"Failed to fetch historical jobs: {e}")
    return applied_urls

def upload_resume_to_blob(pdf_path):
    if not blob_service_client or not os.path.exists(pdf_path): return "No Resume Uploaded"
    try:
        blob_name = os.path.basename(pdf_path) 
        blob_client = blob_service_client.get_blob_client(container="resumes", blob=blob_name)
        with open(pdf_path, "rb") as data: blob_client.upload_blob(data, overwrite=True)
        return blob_client.url
    except Exception: return "Upload Failed"

def log_application(url, job_role, company, location, description, status, resume_url="N/A", portal="Unknown"):
    if not table_client: return
    try:
        safe_desc = description[:30000] if description else "No desc"
        entity = {
            "PartitionKey": portal, "RowKey": str(uuid.uuid4()),
            "JobUrl": url, "JobRole": job_role[:100] if job_role else "Unknown", 
            "Company": company[:100] if company else "Unknown",
            "Location": location[:100] if location else "USA",
            "Description": safe_desc, "Status": status, 
            "DateLogged": time.strftime("%Y-%m-%d %H:%M:%S"), "ResumeUrl": resume_url
        }
        table_client.create_entity(entity=entity)
        print(f"--> Logged to DB: [{status}] | {job_role} at {company} ({portal})")
    except: pass

# --- 3. UNIVERSAL FORM SOLVERS ---
def solve_custom_questions(page, fname, lname, mail, ph):
    """Universal React-Bypass. Works across all portals."""
    for frame in page.frames:
        try:
            frame.evaluate(f'''([fname, lname, mail, ph]) => {{
                document.querySelectorAll('select').forEach(s => {{
                    if (s.options.length > 1 && (!s.value || s.selectedIndex <= 0)) {{
                        const nativeSelectValueSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value') ? Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set : null;
                        let val = s.options[1].value;
                        const parentText = (s.closest('div') || s.parentElement).innerText.toLowerCase();
                        if (parentText.includes('citizen') || parentText.includes('authorization') || parentText.includes('status')) {{
                            for (let i = 0; i < s.options.length; i++) {{
                                let optText = s.options[i].text.toLowerCase();
                                if (optText.includes('citizen') || optText.includes('authorized') || optText.includes('green card')) {{ val = s.options[i].value; break; }}
                            }}
                        }}
                        if (nativeSelectValueSetter) {{ nativeSelectValueSetter.call(s, val); }} else {{ s.value = val; }}
                        s.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }});
                const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                const names = [...new Set(radios.map(r => r.name))];
                names.forEach(name => {{
                    const group = document.querySelectorAll(`input[name="${{name}}"]`);
                    let isAnswered = false; group.forEach(r => {{ if (r.checked) isAnswered = true; }});
                    if (!isAnswered && group.length > 0) {{
                        let clicked = false;
                        group.forEach(r => {{
                            const text = (r.nextElementSibling ? r.nextElementSibling.innerText : '').toLowerCase() + ' ' + (r.parentElement ? r.parentElement.innerText : '').toLowerCase();
                            const val = r.value.toLowerCase(); const parentText = (r.closest('div') || r.parentElement).innerText.toLowerCase();
                            if (text.includes('citizen') || text.includes('green card') || text.includes('authorized')) {{
                                r.dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); r.checked = true; r.dispatchEvent(new Event('change', {{ bubbles: true }})); clicked = true;
                            }} else if (text.includes('yes') || val === 'yes' || val === 'y') {{
                                if (!parentText.includes('sponsorship') && !parentText.includes('require visa')) {{ r.dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); r.checked = true; r.dispatchEvent(new Event('change', {{ bubbles: true }})); clicked = true; }}
                            }} else if (text.includes('no') || val === 'no' || val === 'n') {{
                                if (parentText.includes('sponsorship') || parentText.includes('require visa')) {{ r.dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); r.checked = true; r.dispatchEvent(new Event('change', {{ bubbles: true }})); clicked = true; }}
                            }}
                        }});
                        if (!clicked) {{ group[0].dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); group[0].checked = true; group[0].dispatchEvent(new Event('change', {{ bubbles: true }})); }}
                    }}
                }});
                document.querySelectorAll('input[type="checkbox"]').forEach(c => {{ if (!c.checked) {{ c.dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); c.checked = true; c.dispatchEvent(new Event('change', {{ bubbles: true }})); }} }});
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value') ? Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set : null;
                const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value') ? Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set : null;
                document.querySelectorAll('input, textarea').forEach(i => {{
                    if (i.value || i.readOnly || i.disabled || window.getComputedStyle(i).visibility === 'hidden') return;
                    if (i.type === 'radio' || i.type === 'checkbox' || i.type === 'submit' || i.type === 'file' || i.type === 'hidden' || i.type === 'button') return;
                    const name = (i.name || '').toLowerCase(); const placeholder = (i.placeholder || '').toLowerCase(); const type = (i.type || '').toLowerCase();
                    let fillValue = null;
                    if (name.includes('first') || placeholder.includes('first')) {{ fillValue = fname; }} 
                    else if (name.includes('last') || placeholder.includes('last')) {{ fillValue = lname; }} 
                    else if (name.includes('name') || placeholder.includes('name')) {{ fillValue = fname + " " + lname; }} 
                    else if (name.includes('email') || placeholder.includes('email') || type === 'email') {{ fillValue = mail; }} 
                    else if (name.includes('phone') || placeholder.includes('phone') || type === 'tel') {{ fillValue = ph; }} 
                    else if (type === 'number' || name.includes('year') || name.includes('exp')) {{ fillValue = "9"; }} 
                    else if (type === 'text' || type === 'textarea') {{ fillValue = "Yes"; }} 
                    if (fillValue) {{
                        if (i.tagName === 'TEXTAREA' && nativeTextAreaValueSetter) {{ nativeTextAreaValueSetter.call(i, fillValue); }} 
                        else if (nativeInputValueSetter) {{ nativeInputValueSetter.call(i, fillValue); }} 
                        else {{ i.value = fillValue; }}
                        i.dispatchEvent(new Event('input', {{ bubbles: true }})); i.dispatchEvent(new Event('change', {{ bubbles: true }})); i.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }}
                }});
            }}''', [fname, lname, mail, ph])
        except: pass

def universal_click(page, keywords, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        for frame in page.frames:
            try:
                clicked = frame.evaluate('''([keywords]) => {
                    function pierce(root) {
                        let found = null;
                        const els = root.querySelectorAll('*');
                        for (let el of els) {
                            if (el.shadowRoot) { let res = pierce(el.shadowRoot); if (res) found = res; }
                            if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button' || (el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button'))) {
                                if (el.disabled || window.getComputedStyle(el).visibility === 'hidden') continue;
                                const txt = (el.innerText || el.value || '').toLowerCase().trim();
                                for (let k of keywords) {
                                    if (txt === k || (k !== 'submit' && txt.includes(k))) { found = el; break; }
                                }
                            }
                            if (found) break;
                        }
                        return found;
                    }
                    const btn = pierce(document);
                    if (btn) { btn.dispatchEvent(new PointerEvent('click', { view: window, bubbles: true, cancelable: true, buttons: 1 })); return true; }
                    return false;
                }''', [keywords])
                if clicked: return True
            except: continue
        time.sleep(1)
    return False

# --- 4. MULTI-PORTAL RECONNAISSANCE ---
def inject_cookies(context):
    """Parses JSON cookie strings and injects them into the browser context to bypass Passkeys"""
    print("\n--- 🍪 Injecting Session Cookies for Passwordless Portals ---")
    
    if INDEED_COOKIES:
        try:
            cookies = json.loads(INDEED_COOKIES)
            clean_cookies = [{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/")} for c in cookies]
            context.add_cookies(clean_cookies)
            print("✅ Indeed Cookies Injected Successfully")
        except Exception as e: print(f"❌ Failed to parse Indeed cookies: {e}")
        
    if ZIP_COOKIES:
        try:
            cookies = json.loads(ZIP_COOKIES)
            clean_cookies = [{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/")} for c in cookies]
            context.add_cookies(clean_cookies)
            print("✅ ZipRecruiter Cookies Injected Successfully")
        except Exception as e: print(f"❌ Failed to parse ZipRecruiter cookies: {e}")

def login_to_portals(page):
    print("\n--- 🔐 Authenticating with Job Portals ---")
    
    # 1. Standard Password Logins (Dice & Monster)
    if DICE_USERNAME:
        try:
            page.goto("https://www.dice.com/dashboard/login", timeout=30000)
            page.locator('input[type="email"]:visible').first.fill(DICE_USERNAME)
            page.locator('button:has-text("Continue"), button:has-text("Next")').first.click()
            time.sleep(2)
            page.locator('input[type="password"]:visible').first.fill(DICE_PASSWORD)
            page.locator('button:has-text("Sign In"), button[type="submit"]').first.click()
            time.sleep(3)
            print("✅ Dice Login Successful")
        except: print("❌ Dice Login Failed")

    if MONSTER_USERNAME:
        try:
            page.goto("https://www.monster.com/profile/login", timeout=30000)
            page.locator('input[type="email"]').first.fill(MONSTER_USERNAME)
            page.locator('input[type="password"]').first.fill(MONSTER_PASSWORD)
            page.locator('button[type="submit"], button:has-text("Log In")').first.click()
            time.sleep(3)
            print("✅ Monster Login Successful")
        except: print("❌ Monster Login Failed")

def gather_job_urls(page):
    master_queue = []
    
    # 1. DICE QUEUE
    dice_urls = [
        'https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&countryCode=US&filters.easyApply=true&filters.workplaceTypes=Remote',
        'https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&location=Dallas,+TX&radius=30&filters.easyApply=true'
    ]
    for url in dice_urls:
        try:
            page.goto(url, timeout=30000)
            time.sleep(4)
            links = page.locator('a[href*="/job-detail/"]').all()
            for link in links:
                href = link.get_attribute('href')
                if href: master_queue.append(("Dice", href.split('?')[0] if href.startswith('http') else f"https://www.dice.com{href.split('?')[0]}"))
        except: pass

    # 2. ZIPRECRUITER QUEUE (1-Click Apply Only)
    zip_urls = [
        'https://www.ziprecruiter.com/jobs-search?search=DevOps+Architect&location=Remote&refine_by_tags=1_click_apply',
        'https://www.ziprecruiter.com/jobs-search?search=DevOps+Architect&location=Dallas%2C+TX&radius=25&refine_by_tags=1_click_apply'
    ]
    for url in zip_urls:
        try:
            page.goto(url, timeout=30000)
            time.sleep(4)
            links = page.locator('a.job_link').all()
            for link in links:
                href = link.get_attribute('href')
                if href: master_queue.append(("ZipRecruiter", href.split('?')[0]))
        except: pass

    # 3. INDEED QUEUE (Easy Apply Only)
    indeed_urls = [
        'https://www.indeed.com/jobs?q=DevOps+Architect&l=Remote&sc=0kf%3Aattr%28DSQF7%29%3B',
        'https://www.indeed.com/jobs?q=DevOps+Architect&l=Dallas%2C+TX&sc=0kf%3Aattr%28DSQF7%29%3B' 
    ]
    for url in indeed_urls:
        try:
            page.goto(url, timeout=30000)
            time.sleep(4)
            links = page.locator('a.jcs-JobTitle').all()
            for link in links:
                href = link.get_attribute('href')
                if href: 
                    full_url = href if href.startswith('http') else f"https://www.indeed.com{href}"
                    master_queue.append(("Indeed", full_url.split('&')[0]))
        except: pass

    # Remove duplicates from the scrape phase
    return list({v[1]:v for v in master_queue}.values())

# --- 5. THE UNIVERSAL APPLICATION ENGINE ---
def process_master_queue(page, master_queue, applied_urls):
    for portal, url in master_queue:
        if url in applied_urls:
            continue

        print(f"\n[{portal}] Navigating to: {url}")
        try:
            page.goto(url, timeout=30000)
            time.sleep(3)
            
            # Universal data extraction
            job_role = page.title().split('-')[0].split('|')[0].strip()
            try: company = page.locator('.companyName, .employer-name, a[data-cy="companyNameLink"], .jobs-unified-top-card__company-name').first.inner_text(timeout=2000)
            except: company = "Unknown Company"
            try: job_location = page.locator('.jobsearch-JobInfoHeader-subtitle, [data-cy="location"], .jobs-unified-top-card__bullet').first.inner_text(timeout=2000)
            except: job_location = "USA"
            try: description_text = page.locator('#jobdescSec, #jobDescriptionText, .jobs-description__content, .description').first.inner_text(timeout=2000)
            except: description_text = page.locator('body').inner_text()

            # AI Evaluation
            is_match = evaluate_job(description_text)
            if not is_match:
                print("❌ OpenAI rejected this role.")
                log_application(url, job_role, company, job_location, description_text, "Rejected by AI", "N/A", portal)
                applied_urls.add(url)
                continue

            print("✅ OpenAI approved! Generating tailored resume...")
            try:
                dynamic_resume_path = generate_tailored_resume(description_text, job_role, company)
                resume_link = upload_resume_to_blob(dynamic_resume_path)
            except Exception as e:
                print(f"⚠️ Resume generation failed: {e}")
                dynamic_resume_path = RESUME_PATH
                resume_link = "N/A"

            # Check if already applied (UI Check)
            if page.evaluate("() => document.body.innerText.toLowerCase().includes('already applied') || document.body.innerText.toLowerCase().includes('applied to this job')"):
                print("⚠️ Already applied natively! Skipping.")
                log_application(url, job_role, company, job_location, description_text, "Already Applied", resume_link, portal)
                applied_urls.add(url)
                continue

            # The Universal Form Loop
            print(f"-> Initiating {portal} Application sequence...")
            universal_click(page, ['apply now', 'apply', 'easy apply', '1-click apply', 'quick apply'], timeout=5)
            time.sleep(4) 

            name_parts = CANDIDATE_NAME.split()
            fname, lname = name_parts[0], " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            for step in range(10): 
                for frame in page.frames:
                    try:
                        file_input = frame.locator('input[type="file"]').first
                        if file_input.is_visible(timeout=500):
                            file_input.set_input_files(dynamic_resume_path)
                            print(f"-> Uploaded {os.path.basename(dynamic_resume_path)}")
                    except: pass

                solve_custom_questions(page, fname, lname, CANDIDATE_EMAIL, CANDIDATE_PHONE)
                time.sleep(1)
                
                if universal_click(page, ['submit application', 'submit', 'finish application', 'finish', 'send'], timeout=3):
                    print("-> 🚀 Clicked Submit!")
                    time.sleep(5)
                    log_application(url, job_role, company, job_location, description_text, "Approved & Applied", resume_link, portal)
                    break
                elif universal_click(page, ['next', 'continue', 'review', 'skip'], timeout=3):
                    print("-> Clicked Next/Continue.")
                    time.sleep(2)
                else:
                    print("-> Stuck on form. Could not find Next or Submit.")
                    log_application(url, job_role, company, job_location, description_text, "Approved but Failed", resume_link, portal)
                    break
            
            # REAL-TIME MEMORY UPDATE
            applied_urls.add(url)
            
        except Exception as inner_e:
            print(f"Skipping job. Error: {inner_e}")

def run_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"])
        
        # We must create the context first so we can inject the cookies
        context = browser.new_context()
        
        # INJECT PASSKEY COOKIES BEFORE OPENING A PAGE
        inject_cookies(context)
        
        page = context.new_page()
        stealth_sync(page) 
        
        applied_urls = get_previously_applied_jobs()
        
        # LOGIN TO PASSWORD SITES
        login_to_portals(page)
        
        print("\n--- 🔍 SCRAPING PHASE: Building Master Queue ---")
        master_queue = gather_job_urls(page)
        print(f"Total Unique Jobs Found Across Portals: {len(master_queue)}")
        
        print("\n--- 🚀 APPLICATION PHASE: Processing Queue ---")
        process_master_queue(page, master_queue, applied_urls)
        
        browser.close()

if __name__ == "__main__":
    run_scraper()