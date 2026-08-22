import os
import re
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import requests
from bs4 import BeautifulSoup
import network_utils
from urllib.parse import urljoin, urlparse

# Regular expression to identify standard email formats
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

def clean_url(url):
    """Ensures the URL has a proper scheme (http/https)."""
    if not url or pd.isna(url):
        return None
    url = str(url).strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def extract_emails_from_url(url):
    """Fetches a URL and extracts unique email addresses."""
    cleaned_url = clean_url(url)
    if not cleaned_url:
        return "None Found"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    all_emails = set()
    target_keywords = ['contact', 'about', 'support', 'team', 'reach']
    
    while True:
        try:
            # 5-second timeout ensures the script doesn't hang on slow sites
            response = requests.get(cleaned_url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code != 200:
                return "None Found"
                
            # Search the raw HTML text for emails
            soup = BeautifulSoup(response.text, 'html.parser')
            all_emails.update(re.findall(EMAIL_REGEX, soup.get_text()))
            
            # Also check mailto links specifically
            for link in soup.find_all('a', href=True):
                if link['href'].startswith('mailto:'):
                    email = link['href'].replace('mailto:', '').split('?')[0].strip()
                    if re.match(EMAIL_REGEX, email):
                        all_emails.add(email)
                        
            # --- FIND RELEVANT SUBPAGES ---
            base_url = response.url # use final redirected url
            parsed_base = urlparse(base_url)
            base_domain = parsed_base.netloc
            
            subpages_to_visit = set()
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                text = link.get_text().strip().lower()
                href_lower = href.lower()
                
                # Check if it matches our keywords
                if any(kw in href_lower or kw in text for kw in target_keywords):
                    # Resolve relative url
                    full_url = urljoin(base_url, href)
                    parsed_full = urlparse(full_url)
                    
                    # Ensure it's internal
                    if parsed_full.netloc == base_domain or parsed_full.netloc == "":
                        subpages_to_visit.add(full_url)
            
            # Limit to max 5 subpages to avoid crawling too much
            subpages_to_visit = list(subpages_to_visit)[:5]
            
            # Fetch subpages
            for subpage_url in subpages_to_visit:
                # Avoid re-fetching the homepage if the link just points back to it
                if subpage_url.rstrip('/') == base_url.rstrip('/'):
                    continue
                    
                try:
                    sub_resp = requests.get(subpage_url, headers=headers, timeout=5, allow_redirects=True)
                    if sub_resp.status_code == 200:
                        sub_soup = BeautifulSoup(sub_resp.text, 'html.parser')
                        all_emails.update(re.findall(EMAIL_REGEX, sub_soup.get_text()))
                        for link in sub_soup.find_all('a', href=True):
                            href = link['href']
                            if href.startswith('mailto:'):
                                email = href.replace('mailto:', '').split('?')[0].strip()
                                if re.match(EMAIL_REGEX, email):
                                    all_emails.add(email)
                except Exception:
                    pass
            
            return ", ".join(all_emails) if all_emails else "None Found"
            
        except Exception:
            if not network_utils.is_internet_available():
                network_utils.wait_for_network()
                continue
            # Fails silently and continues if a site is broken or times out
            return "None Found"

def select_file_via_gui():
    """Opens a Tkinter file dialog to pick the CSV file."""
    root = tk.Tk()
    root.withdraw() # Hide the main tiny tkinter window
    root.attributes('-topmost', True) # Bring the file dialog window to the front
    
    print("📁 Please select your CSV file from the popup window...")
    file_path = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    return file_path

def main():
    # 1. Use Tkinter to get the file path
    csv_filename = select_file_via_gui()
    
    if not csv_filename:
        print("❌ Action cancelled. No file selected.")
        return

    print(f"📖 Reading: {csv_filename}...")
    df = pd.read_csv(csv_filename)
    
    # 2. Identify the column name (searches for 'link' or 'website')
    url_column = None
    possible_headers = ['link', 'website', 'url', 'links', 'websites']
    
    for header in df.columns:
        if str(header).lower().strip() in possible_headers:
            url_column = header
            break
            
    if not url_column:
        print(f"❌ Could not automatically find a URL column. Available columns: {list(df.columns)}")
        url_column = input("Please manually type the exact name of your URL column: ").strip()
        if url_column not in df.columns:
            print("❌ Invalid column name. Exiting.")
            return

    print(f"🔍 Found URL column: '{url_column}'")
    
    # 3. Process and update row by row
    total_rows = len(df)
    emails_list = []
    
    for index, row in df.iterrows():
        url = row[url_column]
        print(f"Processing [{index + 1}/{total_rows}]: {url}")
        
        emails = extract_emails_from_url(url)
        emails_list.append(emails)
        
    # 4. Save the results directly back into the SAME CSV file
    df['Scraped_Emails'] = emails_list
    df.to_csv(csv_filename, index=False)
    
    print(f"\n🎉 Done! The emails have been saved directly back into '{csv_filename}'")

if __name__ == "__main__":
    main()