import os
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from brain import evaluate_job  # Your OpenAI logic

# 1. Pull secure details from Environment Variables
CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vamshi Krishna Boddu")
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL")
LINKEDIN_URL = os.getenv("LINKEDIN_URL")
LOCATION = os.getenv("CANDIDATE_LOCATION", "Frisco, Texas")
RESUME_PATH = "/app/resume.pdf"

def apply_on_dice(page):
    print("--- Starting Dice Job Search ---")
    page.goto('https://www.dice.com/jobs?q=Technology+Architect&location=Frisco,+TX&filters.easyApply=true')
    
    try:
        # 1. Wait for the filter sidebar to prove the page loaded
        page.wait_for_selector('text="How far are you willing to commute"', timeout=30000)
        
        # 2. Target the job title links directly instead of the old card wrapper
        page.wait_for_selector('a.card-title-link', timeout=15000)
        job_links = page.locator('a.card-title-link').all()
        print(f"Found {len(job_links)} Easy Apply jobs on Dice.")

        for link in job_links:
            # Click the link
            link.click()
            page.wait_for_load_state('networkidle')
            time.sleep(2) 
            
            # 3. Extract description using multiple possible locators just to be safe
            description_text = page.locator('#jobdescSec, .job-description, [data-cy="job-description"]').first.inner_text()
            print(f"Extracted description. Sending to OpenAI...")
            
            # Pass to OpenAI
            is_match = evaluate_job(description_text)
            
            if is_match:
                print("OpenAI approved! Applying...")
                page.locator('button.btn-primary:has-text("Apply Now")').click()
                page.locator('input[name="firstName"]').fill(CANDIDATE_NAME.split()[0])
                page.locator('input[name="lastName"]').fill(CANDIDATE_NAME.split()[-1])
                page.locator('input[name="email"]').fill(CANDIDATE_EMAIL)
                page.locator('input[type="file"]').set_input_files(RESUME_PATH)
                page.locator('button:has-text("Submit")').click()
            else:
                print("OpenAI rejected this role. Skipping.")
                
            print("Evaluated Dice job.")
            
    except Exception as e:
        print(f"Dice timeout. The page title is: '{page.title()}'")
        print(f"Exact error: {e}")
        print(f"Dice scraping encountered an error or no jobs found: {e}")

def apply_on_indeed(page):
    print("--- Starting Indeed Job Search ---")
    # Using Frisco, TX specifically to narrow down the search
    page.goto('https://www.indeed.com/jobs?q=DevOps+Engineer&l=Frisco,+TX')
    
    try:
        page.wait_for_selector('td.resultContent', timeout=60000)
        job_cards = page.locator('td.resultContent').all()
        print(f"Found {len(job_cards)} total jobs on Indeed page.")

        for card in job_cards:
            # ONLY click jobs that have the "Easily apply" tag
            if card.locator('span:has-text("Easily apply")').is_visible():
                card.click()
                page.wait_for_selector('#jobsearch-ViewjobPaneWrapper')
                time.sleep(2)
                
                # TODO: Extract description from the right pane, pass to evaluate_job()
                # If evaluate_job() == True:
                #     page.locator('#jobsearch-ViewjobPaneWrapper').get_by_role("button", name="Apply now").click()
                #     page.get_by_label("First name").fill(CANDIDATE_NAME.split()[0])
                #     page.get_by_label("Last name").fill(CANDIDATE_NAME.split()[-1])
                #     page.get_by_label("Email").fill(CANDIDATE_EMAIL)
                #     page.locator('input[type="file"]').set_input_files(RESUME_PATH)
                #     page.get_by_role("button", name="Continue").click()
                
                print("Evaluated Indeed job.")
    except Exception as e:
        print(page.title())
        print(f"Page Text: {page.locator('body').inner_text()[:1000]}")      
        print(f"Exact error: {e}")
        print(f"Indeed scraping encountered an error: {e}")

def run_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Using a context helps isolate cookies and cache between runs
        context = browser.new_context()
        page = context.new_page()
        
        # Apply stealth tactics to bypass Cloudflare/DataDome
        stealth_sync(page) 
        
        # Run Dice first
        apply_on_dice(page)
        
        # Run Indeed second
        # apply_on_indeed(page)
        
        browser.close()
        print("--- Daily Job Hunt Complete ---")

if __name__ == "__main__":
    run_scraper()