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
        # 1. Wait for the page's background network requests to stop downloading
        page.wait_for_load_state('networkidle', timeout=30000)
        time.sleep(3) # Give the browser an extra 3 seconds to visually paint the screen
        
        # 2. Look for the job links. 
        job_links = page.locator('a.card-title-link').all()
        
        if len(job_links) == 0:
            print("Standard link class not found. Trying fallback URL selector...")
            # Fallback: Grab any link on the page that points to a job detail page
            job_links = page.locator('a[href*="/job-detail/"]').all()
            
        print(f"Found {len(job_links)} Easy Apply jobs on Dice.")

        # Let's just evaluate the first 5 jobs for this test run so it doesn't take an hour
        for link in job_links[:5]:
            link.click()
            
            # Wait for the right-side panel to load the job description
            page.wait_for_load_state('networkidle')
            time.sleep(2) 
            
            # 3. Extract description using multiple possible CSS locators
            description_text = page.locator('#jobdescSec, .job-description, [data-cy="job-description"]').first.inner_text()
            print(f"Extracted description. Sending to OpenAI for evaluation...")
            
            # Pass to your OpenAI brain
            is_match = evaluate_job(description_text)
            
            if is_match:
                print("OpenAI approved! Applying...")
                # We will leave the click actions commented out just for this one test 
                # to make sure it grades correctly without accidentally applying to garbage.
                # page.locator('button.btn-primary:has-text("Apply Now")').click()
                # page.locator('input[name="firstName"]').fill(CANDIDATE_NAME.split()[0])
                # page.locator('input[name="lastName"]').fill(CANDIDATE_NAME.split()[-1])
                # page.locator('input[name="email"]').fill(CANDIDATE_EMAIL)
                # page.locator('input[type="file"]').set_input_files(RESUME_PATH)
                # page.locator('button:has-text("Submit")').click()
            else:
                print("OpenAI rejected this role. Skipping.")
                
            print("--- Moving to next job ---")
            
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