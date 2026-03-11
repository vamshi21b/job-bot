import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

def setup_browser(p):
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    stealth_sync(page)
    return browser, page

def find_and_apply(page, target_role, target_location):
    search_url = f"https://example-job-board.com/search?q={target_role}&loc={target_location}"
    page.goto(search_url)
    time.sleep(3) 
    
    job_cards = page.query_selector_all('.job-card')
    extracted_jobs = []
    
    for card in job_cards:
        title = card.query_selector('.job-title').inner_text()
        link = card.query_selector('a').get_attribute('href')
        
        job_page = page.context.new_page()
        stealth_sync(job_page)
        job_page.goto(link)
        time.sleep(2)
        
        try:
            description = job_page.query_selector('.job-description').inner_text()
            extracted_jobs.append({"title": title, "link": link, "description": description})
        except Exception:
            pass
        finally:
            job_page.close()
            
    return extracted_jobs

def submit_application(page, job_link, tailored_snippet):
    page.goto(job_link)
    time.sleep(2)
    
    try:
        page.click('button:has-text("Apply")')
        time.sleep(1)
        
        page.fill('input[name="firstName"]', "Vamshi")
        page.fill('input[name="lastName"]', "Boddu")
        
        if page.is_visible('textarea[name="coverLetter"]'):
            page.fill('textarea[name="coverLetter"]', tailored_snippet)
            
        # page.click('button[type="submit"]') # Uncomment when ready for production
        print(f"Successfully processed application for: {job_link}")
    except Exception as e:
        print(f"Failed to apply at {job_link}: {e}")