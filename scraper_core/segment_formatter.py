import json
import os
import csv
import re
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIR = os.path.join(BASE_DIR, 'admin')
CONFIG_JSON = os.path.join(ADMIN_DIR, 'current_task_config.json')

# Input / Output directories
PRE_SEGMENT_DIR = os.path.join(BASE_DIR, 'pre_segment_csvs')
UPLOADABLE_DIR = os.path.join(BASE_DIR, 'uploadable_csvs')

INPUT_FILE = os.path.join(BASE_DIR, 'FinalEmails.csv')

def load_config():
    if os.path.exists(CONFIG_JSON):
        with open(CONFIG_JSON, 'r') as f:
            return json.load(f)
    return {}

def format_datetime(iso_string):
    dt = datetime.fromisoformat(iso_string)
    date_str = dt.strftime("%d%b%Y")
    time_str = dt.strftime("%H%M")
    return date_str, time_str

def main():
    config = load_config()
    if not config:
        print("[!] Could not load config. Ensure task config exists.")
        return

    initial_wording = config.get("initial_wording", "segment_")
    search_terms = config.get("search_terms", ["Unknown"])
    first_search_term = search_terms[0].replace(' ', '')
    locality = config.get("locality", "Unknown").replace(' ', '')
    
    # Use started_at if available, otherwise created_at
    timestamp_iso = config.get("started_at", config.get("created_at", datetime.now().isoformat()))
    
    date_str, time_str = format_datetime(timestamp_iso)
    
    base_file_name = f"{first_search_term}_{locality}_{date_str}_{time_str}"
    
    if not os.path.exists(PRE_SEGMENT_DIR):
        os.makedirs(PRE_SEGMENT_DIR)
        
    if not os.path.exists(UPLOADABLE_DIR):
        os.makedirs(UPLOADABLE_DIR)
        
    pre_segment_file = os.path.join(PRE_SEGMENT_DIR, f"{base_file_name}.csv")
    uploadable_file = os.path.join(UPLOADABLE_DIR, f"{base_file_name}.csv")
    
    if not os.path.exists(INPUT_FILE):
        print(f"[!] Input file {INPUT_FILE} not found. Ensure cleaner.py ran successfully.")
        return

    # Compile regexes
    tld_regex = r'\.(com|org|net|edu|gov|co|us|info|io|events|me|tv|biz|design|studio|photography|agency|uk|ca|au|in|co\.uk)'
    email_regex = re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+' + tld_regex + r')', re.IGNORECASE)

    prefixes_to_strip = [
        r'^www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'^\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        r'^\d{1,3}[-.\s]?\d{3}[-.\s]?\d{4}',
        r'^\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        r'^\d{3}[-.\s]?\d{4}',
        r'^\d{4,5}(?=[a-zA-Z])', # 4-5 digit codes followed by letter
        r'^[0-9+-.]{8,}(?=[a-zA-Z])', # Any long sequence of numbers/dashes/dots
        r'^(Email|US|Us|States|Worldwide|Decor|Contact|Instagram|Facebook|Phone|Tel|Mobile|Cell)',
        r'^[0-9a-zA-Z.\-+]+?(?=hello@|info@|contact@|sales@|admin@|support@|frontdesk)',
        r'^\d{1,2}(am|pm)?[-.\s]?\d{1,2}(am|pm)?contact\+?\d{10,11}', # specific catch for 10am-5pmcontact+19167902779
        r'^items\.',
        r'^00pm',
    ]
    compiled_prefixes = [re.compile(p, re.IGNORECASE) for p in prefixes_to_strip]

    unique_emails = set()
    total_rows = 0
    rejected_rows = 0

    print("[*] Stage A: Reading and cleaning emails...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            total_rows += 1
            line = line.strip(' "\'\n\r\t')
            
            if not line:
                continue
            
            if line.startswith('%') or line.startswith('+91') or line.startswith('+'):
                rejected_rows += 1
                continue

            cleaned_line = line
            changed = True
            while changed:
                changed = False
                new_line = re.sub(r'^[-+.\s]+', '', cleaned_line)
                if new_line != cleaned_line:
                    cleaned_line = new_line
                    changed = True
                    
                for prefix_regex in compiled_prefixes:
                    new_line = prefix_regex.sub('', cleaned_line)
                    if new_line != cleaned_line:
                        cleaned_line = new_line
                        changed = True

            match = email_regex.search(cleaned_line)
            if match:
                extracted_email = match.group(1).lower()
                if extracted_email and extracted_email[0].isdigit():
                    rejected_rows += 1
                else:
                    unique_emails.add(extracted_email)
            else:
                rejected_rows += 1

    # Save to Pre-Segment (Stage A)
    print(f"[*] Saving {len(unique_emails)} cleaned emails to pre_segment_csvs...")
    with open(pre_segment_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Email'])
        for email in sorted(unique_emails):
            writer.writerow([email])

    # Save to Uploadable (Stage B)
    print(f"[*] Stage B: Formatting segment and saving to uploadable_csvs...")
    with open(uploadable_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Email'])
        
        for index, email in enumerate(sorted(unique_emails), start=1):
            row_id = f"{initial_wording}{base_file_name}_{index}"
            writer.writerow([row_id, email])
            
    print(f"[+] Total Rows Processed: {total_rows}")
    print(f"[+] Total Rows Rejected/Unmatched: {rejected_rows}")
    print(f"[+] Total Unique Valid Emails Found: {len(unique_emails)}")
    print(f"[+] Segment Formatter completed successfully!")

if __name__ == '__main__':
    main()
