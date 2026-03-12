import os
import csv
from azure.data.tables import TableClient
from dotenv import load_dotenv

# Load local environment variables from the .env file
load_dotenv()

# Pull the secret dynamically
CONNECTION_STRING = os.getenv("STORAGE_CONN_STR")
TABLE_NAME = "AppliedJobs"
OUTPUT_FILE = "applied_jobs_log.csv"

def export_to_csv():
    # Safety check to ensure the .env file is being read correctly
    if not CONNECTION_STRING:
        print("Error: STORAGE_CONN_STR environment variable is missing.")
        print("Please ensure your .env file is in the same directory and contains your connection string.")
        return
        
    try:
        print(f"Connecting to Azure Table: {TABLE_NAME}...")
        table_client = TableClient.from_connection_string(conn_str=CONNECTION_STRING, table_name=TABLE_NAME)
        
        # Pull all records from the database
        print("Fetching records...")
        entities = list(table_client.list_entities())
        
        if not entities:
            print("No jobs found in the database yet. Let the bot run a few times first!")
            return

        print(f"Found {len(entities)} job applications. Exporting to {OUTPUT_FILE}...")
        
        # Define the exact columns we want in our Excel file
        fieldnames = ["DateApplied", "JobRole", "Company", "Location", "JobUrl"]
        
        # Write the data to a CSV
        with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as file:
            # We use extrasaction='ignore' so we don't accidentally print the massive 30,000 character descriptions into the spreadsheet
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for entity in entities:
                writer.writerow(entity)
                
        print(f"Success! Export complete. You can now open '{OUTPUT_FILE}' in Excel.")

    except Exception as e:
        print(f"An error occurred while connecting or exporting: {e}")

if __name__ == "__main__":
    export_to_csv()