import csv
import re
import os

def clean_email_data():
    input_file = 'Final_Pure_Emails.csv'
    output_dir = 'output'
    output_file = os.path.join(output_dir, 'Final_Pure_Emails.csv')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

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

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_rows += 1
            line = line.strip(' "\'\n\r\t')
            
            # Skip empty lines
            if not line:
                continue

            # Initial rejection
            if line.startswith('%') or line.startswith('+91') or line.startswith('+'):
                rejected_rows += 1
                continue

            # Strip prefixes iteratively
            cleaned_line = line
            changed = True
            while changed:
                changed = False
                # Remove leading hyphens or spaces which might prevent regex from matching phone numbers
                new_line = re.sub(r'^[-+.\s]+', '', cleaned_line)
                if new_line != cleaned_line:
                    cleaned_line = new_line
                    changed = True
                    
                for prefix_regex in compiled_prefixes:
                    new_line = prefix_regex.sub('', cleaned_line)
                    if new_line != cleaned_line:
                        cleaned_line = new_line
                        changed = True

            # Extract core email
            match = email_regex.search(cleaned_line)
            if match:
                extracted_email = match.group(1).lower()
                if extracted_email and extracted_email[0].isdigit():
                    rejected_rows += 1
                else:
                    unique_emails.add(extracted_email)
            else:
                rejected_rows += 1

    # Output to the final CSV file
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Email'])
        for email in sorted(unique_emails):
            writer.writerow([email])

    print(f"Total Rows Processed: {total_rows}")
    print(f"Total Rows Rejected/Unmatched: {rejected_rows}")
    print(f"Total Unique Valid Emails Found: {len(unique_emails)}")
    print(f"Cleaned emails saved to {output_file}")

if __name__ == '__main__':
    clean_email_data()
