import os
import time
import uuid
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from azure.data.tables import TableClient
from azure.storage.blob import BlobServiceClient
from brain import evaluate_job
from resume_builder import generate_tailored_resume

CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vamshi Krishna Boddu")
STORAGE_CONN_STR = os.getenv("STORAGE_CONN_STR")
RESUME_PATH = "/app/resume.pdf"

table_client = None
blob_service_client = None

if STORAGE_CONN_STR:
    try:
        table_client = TableClient.from_connection_string(conn_str=STORAGE_CONN_STR, table_name="AppliedJobs")
        blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
        container_client = blob_service_client.get_container_client("resumes")
        
        if not container_client.exists():
            try:
                # Force a private container to bypass Azure's public access block
                container_client.create_container()
                print("Created private 'resumes' container.")
            except Exception as ce:
                print(f"Failed to create container: {ce}")
                
        print("Successfully connected to Azure Table and Blob Storage.")
    except Exception as e:
        print(f"Warning: Could not connect to Azure Storage. Error: {e}")

def upload_resume_to_blob(pdf_path, job_role, company):
    if not blob_service_client or not os.path.exists(pdf_path):
        return "No Resume Uploaded"
    try:
        # Create a readable file name for your Azure portal
        safe_role = "".join(x for x in job_role if x.isalnum() or x in " -_")[:30].strip()
        safe_comp = "".join(x for x in company if x.isalnum() or x in " -_")[:20].strip()
        blob_name = f"{safe_comp}_{safe_role}_{uuid.uuid4().hex[:4]}.pdf".replace(" ", "_")
        
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
        entity = {
            "PartitionKey": "Dice", "RowKey": str(uuid.uuid4()),
            "JobUrl": url, "JobRole": job_role[:100] if job_role else "Unknown", 
            "Company": company[:100] if company else "Unknown",
            "Location": "Remote/Dallas", "Description": safe_desc,
            "Status": status, "DateLogged": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ResumeUrl": resume_url
        }
        table_client.create_entity(entity=entity)
        print(f"--> Logged to DB: [{status}] | {job_role} at {company}")
    except Exception as e: 
        print(f"DB Log Error: {e}")

def run_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"])
        page = browser.new_context().new_page()
        stealth_sync(page) 
        
        print("--- Starting Dice Job Search (DRY RUN MODE) ---")
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
                        except: 
                            try: company = page.title().replace('| Dice.com', '').split(' - ')[1].strip()
                            except: company = "Unknown Company"

                        try: description_text = page.locator('#jobdescSec, .job-description').first.inner_text(timeout=5000)
                        except: description_text = page.locator('body').inner_text()
                            
                        is_match = evaluate_job(description_text)
                        
                        if is_match:
                            print("✅ OpenAI approved! Generating tailored resume...")
                            resume_link = "N/A"
                            try:
                                dynamic_resume_path = generate_tailored_resume(description_text)
                                resume_link = upload_resume_to_blob(dynamic_resume_path, job_role, company)
                            except Exception as e:
                                print(f"-> ⚠️ Dynamic resume generation failed. Error: {e}")

                            # Log as generated and skip the application process
                            log_application(url, job_role, company, description_text, "Resume Generated (Dry Run)", resume_link)
                            print("-> Dry run complete for this job. Moving to next.")
                            
                        else:
                            print("❌ OpenAI rejected this role. Skipping.")
                            log_application(url, job_role, company, description_text, "Rejected by AI", "N/A")
                            
                    except Exception as inner_e:
                        print(f"Skipping individual job. Error: {inner_e}")
            except Exception as e:
                print(f"Queue error: {e}")

        browser.close()
        print("\n--- Daily Generation Complete ---")

if __name__ == "__main__":
    run_scraper()