import pandas as pd
from pathlib import Path

def clean_emails():
    input_file = Path("Emails_Fetched.csv")
    output_file = Path("Final_Cleaned_Leads.csv")
    
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
    
    final_count = len(df)
    print(f"Exploded multiple emails into separate rows.")
    print(f"Final dataset has {final_count} total emails.")
    
    # Save the output
    df.to_csv(output_file, index=False)
    print(f"Saved cleanly formatted leads to {output_file}!")

if __name__ == "__main__":
    clean_emails()
