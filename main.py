import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from scraper import setup_browser, find_and_apply, submit_application
from brain import evaluate_job

load_dotenv()

TARGET_ROLE = os.getenv("TARGET_ROLE", "DevOps Engineer")
TARGET_LOCATION = os.getenv("TARGET_LOCATION", "Texas")

def main():
    print(f"Starting job hunt for {TARGET_ROLE} in {TARGET_LOCATION}...")
    
    with sync_playwright() as p:
        browser, page = setup_browser(p)
        jobs = find_and_apply(page, TARGET_ROLE, TARGET_LOCATION)
        
        for job in jobs:
            print(f"Evaluating: {job['title']}")
            decision = evaluate_job(job['description'])
            
            if decision.startswith("MATCH"):
                snippet = decision.split("|")[1].strip() if "|" in decision else ""
                print(f"Match found! Applying with snippet...")
                submit_application(page, job['link'], snippet)
            else:
                print("Skipping - Not a strong DevOps match.")
                
        browser.close()

if __name__ == "__main__":
    main()