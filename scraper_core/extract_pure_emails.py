import pandas as pd
from pathlib import Path

def extract_pure_emails():
    input_file = Path("Final_Cleaned_Leads.csv")
    output_file = Path("Final_Pure_Emails.csv")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found! Run clean_emails.py first.")
        return

    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    if 'Scraped_Emails' not in df.columns:
        print("Error: 'Scraped_Emails' column not found in the CSV!")
        return

    # Keep only the emails column
    df = df[['Scraped_Emails']]
    
    # Save the pure output
    df.to_csv(output_file, index=False)
    print(f"Saved pure email list ({len(df)} emails) to {output_file}!")

if __name__ == "__main__":
    extract_pure_emails()
