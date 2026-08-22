import pandas as pd
from pathlib import Path

def run():
    input_file = Path("Emails_Fetched.csv")
    final_output = Path("FinalEmails.csv")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found!")
        return

    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    initial_count = len(df)
    
    if 'Scraped_Emails' not in df.columns:
        print("Error: 'Scraped_Emails' column not found in the CSV!")
        return

    # Filter out empty or invalid rows
    invalid_values = ['No Website Provided', 'None Found']
    df = df.dropna(subset=['Scraped_Emails'])
    df = df[~df['Scraped_Emails'].isin(invalid_values)]
    
    # Also filter out anything that doesn't have an '@' just in case
    df = df[df['Scraped_Emails'].str.contains('@', na=False)]
    
    filtered_count = len(df)
    print(f"Filtered out {initial_count - filtered_count} leads that didn't have emails.")
    
    # Split the comma-separated emails into a list
    df['Scraped_Emails'] = df['Scraped_Emails'].str.split(', ')
    
    # Explode the list into separate rows
    df = df.explode('Scraped_Emails')
    
    print(f"Exploded multiple emails into separate rows.")
    
    # Keep only the emails column and deduplicate
    pure_emails = df[['Scraped_Emails']].dropna().drop_duplicates()
    
    # Apply standard cleaning one more time (which replicates running clean_emails.py twice)
    pure_emails = pure_emails[pure_emails['Scraped_Emails'].str.contains('@', na=False)]
    
    # Save the pure output
    pure_emails.to_csv(final_output, index=False)
    print(f"Saved cleanly formatted Final Emails list ({len(pure_emails)} unique emails) to {final_output}!")

if __name__ == "__main__":
    run()
