import os
import time
import uuid
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
            try:
                container_client.create_container()
            except Exception as ce:
                print(f"Failed to create resumes container: {ce}")
                
        print("Successfully connected to Azure Table and Blob Storage.")
    except Exception as e:
        print(f"Warning: Could not connect to Azure Storage. Error: {e}")

def get_previously_applied_jobs():
    """Fetches all previously processed URLs from Azure DB to prevent duplicate runs."""
    applied_urls = set()
    if table_client:
        try:
            print("-> Fetching historical application data from Azure to prevent duplicates...")
            for entity in table_client.list_entities():
                url = entity.get("JobUrl")
                if url: applied_urls.add(url.split('?')[0])
            print(f"-> Found {len(applied_urls)} previously processed jobs.")
        except Exception as e:
            print(f"Failed to fetch historical jobs: {e}")
    return applied_urls

def upload_resume_to_blob(pdf_path):
    if not blob_service_client or not os.path.exists(pdf_path):
        return "No Resume Uploaded"
    try:
        blob_name = os.path.basename(pdf_path) 
        blob_client = blob_service_client.get_blob_client(container="resumes", blob=blob_name)
        with open(pdf_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        print(f"-> Successfully uploaded PDF to Azure Blob: {blob_name}")
        return blob_client.url
    except Exception as e:
        print(f"Failed to upload resume to blob: {e}")
        return "Upload Failed"

def log_application(url, job_role, company, description, status, resume_url="N/A"):
    if not table_client: return
    try:
        safe_desc = description[:30000] if description else "No desc"
        if not job_role: job_role = "Unknown Role"
        if not company: company = "Unknown Company"
        entity = {
            "PartitionKey": "Dice", "RowKey": str(uuid.uuid4()),
            "JobUrl": url, "JobRole": job_role[:100], "Company": company[:100],
            "Location": "Remote/Dallas", "Description": safe_desc,
            "Status": status, "DateLogged": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ResumeUrl": resume_url
        }
        table_client.create_entity(entity=entity)
        print(f"--> Logged to DB: [{status}] | {job_role} at {company}")
    except: pass

# --- 3. CORE AUTOMATION FUNCTIONS ---
def login_to_dice(page):
    if not DICE_USERNAME or not DICE_PASSWORD: return
    print("\n--- 🔐 Authenticating with Dice ---")
    page.goto('[https://www.dice.com/dashboard/login](https://www.dice.com/dashboard/login)')
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

def solve_custom_questions(page, fname, lname, mail, ph):
    """Aggressively auto-fills required fields using React State Bypass"""
    for frame in page.frames:
        try:
            frame.evaluate(f'''([fname, lname, mail, ph]) => {{
                document.querySelectorAll('select').forEach(s => {{
                    if (s.options.length > 1 && (!s.value || s.selectedIndex <= 0)) {{
                        const nativeSelectValueSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value') ? Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set : null;
                        const val = s.options[1].value;
                        if (nativeSelectValueSetter) {{ nativeSelectValueSetter.call(s, val); }} else {{ s.value = val; }}
                        s.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }});
                
                const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                const names = [...new Set(radios.map(r => r.name))];
                names.forEach(name => {{
                    const group = document.querySelectorAll(`input[name="${{name}}"]`);
                    let isAnswered = false;
                    group.forEach(r => {{ if (r.checked) isAnswered = true; }});
                    
                    if (!isAnswered && group.length > 0) {{
                        let clicked = false;
                        group.forEach(r => {{
                            const text = (r.nextElementSibling ? r.nextElementSibling.innerText : '').toLowerCase() + ' ' + (r.parentElement ? r.parentElement.innerText : '').toLowerCase();
                            const val = r.value.toLowerCase();
                            const parentText = (r.closest('div') || r.parentElement).innerText.toLowerCase();
                            
                            if (text.includes('yes') || val === 'yes' || val === 'y') {{
                                if (!parentText.includes('sponsorship') && !parentText.includes('require visa') && !parentText.includes('clearance')) {{
                                    r.dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); r.checked = true; r.dispatchEvent(new Event('change', {{ bubbles: true }})); clicked = true;
                                }}
                            }} else if (text.includes('no') || val === 'no' || val === 'n') {{
                                if (parentText.includes('sponsorship') || parentText.includes('require visa') || parentText.includes('clearance')) {{
                                    r.dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); r.checked = true; r.dispatchEvent(new Event('change', {{ bubbles: true }})); clicked = true;
                                }}
                            }}
                        }});
                        if (!clicked) {{ group[0].dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); group[0].checked = true; group[0].dispatchEvent(new Event('change', {{ bubbles: true }})); }}
                    }}
                }});
                
                document.querySelectorAll('input[type="checkbox"]').forEach(c => {{
                    if (!c.checked) {{ c.dispatchEvent(new PointerEvent('click', {{ bubbles: true }})); c.checked = true; c.dispatchEvent(new Event('change', {{ bubbles: true }})); }}
                }});
                
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value') ? Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set : null;
                const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value') ? Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set : null;

                document.querySelectorAll('input, textarea').forEach(i => {{
                    if (i.value || i.readOnly || i.disabled || window.getComputedStyle(i).visibility === 'hidden') return;
                    if (i.type === 'radio' || i.type === 'checkbox' || i.type === 'submit' || i.type === 'file' || i.type === 'hidden' || i.type === 'button') return;
                    
                    const name = (i.name || '').toLowerCase(); const placeholder = (i.placeholder || '').toLowerCase(); const type = (i.type || '').toLowerCase();
                    let fillValue = null;
                    
                    if (name.includes('first') || placeholder.includes('first')) {{ fillValue = fname; }} 
                    else if (name.includes('last') || placeholder.includes('last')) {{ fillValue = lname; }} 
                    else if (name.includes('name') || placeholder.includes('name') || name.includes('signature')) {{ fillValue = fname + " " + lname; }} 
                    else if (name.includes('email') || placeholder.includes('email') || type === 'email') {{ fillValue = mail; }} 
                    else if (name.includes('phone') || placeholder.includes('phone') || type === 'tel') {{ fillValue = ph; }} 
                    else if (name.includes('link') || placeholder.includes('linkedin') || type === 'url') {{ fillValue = "[https://linkedin.com/in/vamshikrishnaboddu](https://linkedin.com/in/vamshikrishnaboddu)"; }} 
                    else if (type === 'number' || name.includes('year') || placeholder.includes('year') || name.includes('exp')) {{ fillValue = "8"; }} 
                    else if (name.includes('salary') || placeholder.includes('salary') || name.includes('pay') || name.includes('rate') || name.includes('compensation')) {{ fillValue = "150000"; }}
                    else if (name.includes('location') || placeholder.includes('city') || name.includes('address') || name.includes('state')) {{ fillValue = "Dallas, TX"; }}
                    else if (name.includes('country') || placeholder.includes('country')) {{ fillValue = "United States"; }}
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
                            if (el.shadowRoot) {
                                let res = pierce(el.shadowRoot);
                                if (res) found = res;
                            }
                            if (document.querySelector('seds-modal') && !el.closest('seds-modal') && !window.location.href.includes('iframe')) continue; 
                            
                            if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button' || (el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button'))) {
                                if (el.disabled || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('disabled')) continue;
                                
                                const txt = (el.innerText || el.value || '').toLowerCase().trim();
                                for (let k of keywords) {
                                    if (txt === k || (k !== 'submit' && txt.includes(k))) {
                                        const rect = el.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden') {
                                            found = el; break;
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
            except: continue
        time.sleep(1)
    return False

# --- 4. MAIN PIPELINE ---
def apply_on_dice(page):
    print("--- Starting Dice Job Search ---")
    
    # Pre-fetch applied jobs to prevent duplicates
    applied_urls = get_previously_applied_jobs()
    
    search_urls = [
        '[https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&location=Dallas,+TX&radius=30&radiusUnit=mi&filters.easyApply=true&filters.workplaceTypes=On-Site%7CHybrid](https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&location=Dallas,+TX&radius=30&radiusUnit=mi&filters.easyApply=true&filters.workplaceTypes=On-Site%7CHybrid)',
        '[https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&filters.easyApply=true&filters.workplaceTypes=Remote](https://www.dice.com/jobs?q=Technology+Architect+OR+DevOps&filters.easyApply=true&filters.workplaceTypes=Remote)'
    ]

    for search_url in search_urls:
        print(f"\n--- Scraping Queue: {search_url} ---")
        try:
            page.goto(search_url)
            page.wait_for_load_state('domcontentloaded', timeout=30000)
            time.sleep(3) 
            job_links = page.locator('a.card-title-link').all()
            if not job_links: job_links = page.locator('a[href*="/job-detail/"]').all()
                
            job_urls = list(dict.fromkeys([link.get_attribute('href').split('?')[0] if not link.get_attribute('href').startswith('/') else f"[https://www.dice.com](https://www.dice.com){link.get_attribute('href').split('?')[0]}" for link in job_links if link.get_attribute('href')]))
            print(f"Found {len(job_urls)} UNIQUE jobs on this page.")

            for url in job_urls:
                # DEDUPLICATION CHECK: Skip if already in database
                if url in applied_urls:
                    print(f"-> ⏭️ Already processed in a previous run (found in Azure DB). Skipping: {url}")
                    continue

                print(f"\nNavigating to job: {url}")
                try:
                    page.goto(url)
                    page.wait_for_load_state('domcontentloaded', timeout=15000)
                    time.sleep(2) 
                    
                    try: job_role = page.locator('h1.jobTitle, h1[data-cy="jobTitle"]').first.inner_text(timeout=3000)
                    except: job_role = page.title().replace('| Dice.com', '').split(' - ')[0].strip()
                    
                    try: company = page.locator('a[data-cy="companyNameLink"]').first.inner_text(timeout=3000)
                    except: 
                        try: company = page.title().replace('| Dice.com', '').split(' - ')[1].strip()
                        except: company = "Unknown Company"

                    try: description_text = page.locator('#jobdescSec, .job-description').first.inner_text(timeout=5000)
                    except: description_text = page.locator('body').inner_text()
                        
                    is_match = evaluate_job(description_text)
                    if is_match:
                        print("✅ OpenAI approved! Initiating application sequence...")
                        
                        resume_link = "N/A"
                        try:
                            dynamic_resume_path = generate_tailored_resume(description_text, job_role, company)
                            resume_link = upload_resume_to_blob(dynamic_resume_path)
                        except Exception as e:
                            print(f"-> ⚠️ Dynamic resume generation failed. Falling back to default. Error: {e}")
                            dynamic_resume_path = RESUME_PATH

                        try:
                            is_applied = page.evaluate('''() => {
                                const wc = document.querySelector('apply-button-wc');
                                return (wc && wc.getAttribute('status') === 'applied') || document.body.innerText.includes('Already Applied');
                            }''')
                            if is_applied:
                                print("-> ⚠️ Already applied to this job! Skipping.")
                                log_application(url, job_role, company, description_text, "Already Applied", resume_link)
                                continue

                            print("-> Clicking Apply Button to open modal...")
                            universal_click(page, ['apply now', 'apply', 'easy apply'], timeout=5)
                            time.sleep(5) 
                            
                            name_parts = CANDIDATE_NAME.split()
                            fname = name_parts[0]
                            lname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                            for step in range(8):
                                print(f"-> Form Step {step+1}...")
                                
                                for frame in page.frames:
                                    try:
                                        file_input = frame.locator('input[type="file"]').first
                                        if file_input.is_visible(timeout=500):
                                            file_input.set_input_files(dynamic_resume_path)
                                            print(f"-> Forcibly uploaded {os.path.basename(dynamic_resume_path)} to iframe.")
                                    except: pass

                                solve_custom_questions(page, fname, lname, CANDIDATE_EMAIL, CANDIDATE_PHONE)
                                time.sleep(1)
                                
                                # --- DRY RUN OVERRIDE: Submit button is blocked ---
                                if universal_click(page, ['submit application', 'submit', 'finish application', 'finish', 'send'], timeout=3):
                                    print("-> 🛑 DRY RUN MODE: Found Submit button, but skipping actual click!")
                                    log_application(url, job_role, company, description_text, "Resume Generated (Dry Run)", resume_link)
                                    break
                                # --------------------------------------------------

                                elif universal_click(page, ['next', 'continue', 'skip'], timeout=3):
                                    print("-> Clicked Next/Continue button.")
                                    time.sleep(3)
                                elif universal_click(page, ['apply'], timeout=3):
                                    print("-> Clicked generic 'Apply' button inside modal.")
                                    time.sleep(3)
                                else:
                                    print("-> Stuck on form. Could not find Next or Submit button.")
                                    break
                                        
                        except Exception as apply_err:
                            log_application(url, job_role, company, description_text, "Approved but Failed", resume_link)
                    else:
                        print("OpenAI rejected this role. Skipping.")
                        log_application(url, job_role, company, description_text, "Rejected by AI", "N/A")
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