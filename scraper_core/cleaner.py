import pandas as pd
from pathlib import Path
import os

def run():
    input_file = Path("Emails_Fetched.csv")
    final_output = Path("FinalEmails.csv")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found!")
        return

    print(f"Reading {input_file} in chunks...")
    
    if final_output.exists():
        try: final_output.unlink()
        except: pass

    initial_count = 0
    filtered_count = 0
    seen_emails = set()
    invalid_values = {'No Website Provided', 'None Found'}
    
    for chunk in pd.read_csv(input_file, chunksize=10000):
        initial_count += len(chunk)
        if 'Scraped_Emails' not in chunk.columns:
            continue
            
        chunk = chunk.dropna(subset=['Scraped_Emails'])
        chunk = chunk[~chunk['Scraped_Emails'].isin(invalid_values)]
        chunk = chunk[chunk['Scraped_Emails'].str.contains('@', na=False)]
        
        chunk['Scraped_Emails'] = chunk['Scraped_Emails'].str.split(', ')
        chunk = chunk.explode('Scraped_Emails')
        
        pure_emails = chunk[['Scraped_Emails']].dropna()
        pure_emails = pure_emails[pure_emails['Scraped_Emails'].str.contains('@', na=False)]
        
        # Deduplicate using set
        new_emails = []
        for email in pure_emails['Scraped_Emails']:
            email = str(email).strip()
            if email and email not in seen_emails:
                seen_emails.add(email)
                new_emails.append(email)
                
        filtered_count += len(new_emails)
        
        if new_emails:
            out_df = pd.DataFrame({'Scraped_Emails': new_emails})
            out_df.to_csv(final_output, mode='a', index=False, header=not final_output.exists())

    print(f"Filtered out {initial_count - filtered_count} non-email rows.")
    print(f"Saved cleanly formatted Final Emails list ({len(seen_emails)} unique emails) to {final_output}!")

if __name__ == "__main__":
    run()
