import re

with open("scraper_core/pipeline.py", "r", encoding="utf-8") as f:
    content = f.read()

main_start = content.find("def main():")

new_main = """import csv

def main():
    global total_count, start_time
    print("\\n=======================================")
    print("Starting Sequential Email Scraper Pipeline")
    print("=======================================")
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} does not exist. Please ensure aggregation succeeded.")
        return

    processed_links = set()
    processed_names = set()
    if OUTPUT_CSV.exists():
        try:
            print(f"Found existing output file {OUTPUT_CSV}. Reading to skip already processed leads...")
            with open(OUTPUT_CSV, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'link' in row and row['link']:
                        processed_links.add(str(row['link']))
                    elif 'name' in row and row['name']:
                        processed_names.add(str(row['name']))
            print(f"Loaded {len(processed_links) + len(processed_names)} processed identifiers.")
        except Exception as e:
            print(f"Error reading existing output file: {e}. Proceeding without skipping.")

    print(f"Counting new leads in {INPUT_FILE}...")
    total_count = 0
    try:
        with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'link' in row and str(row['link']) in processed_links:
                    continue
                if 'name' in row and str(row['name']) in processed_names:
                    continue
                total_count += 1
    except Exception as e:
        print(f"Error reading {INPUT_FILE}: {e}")
        return

    if total_count == 0:
        print("No new leads to process. Exiting.")
        return
        
    print(f"Found {total_count} leads to process.")
    start_time = time.time()
    
    # Start worker threads
    threads = []
    for _ in range(NUM_WORKER_THREADS):
        t = threading.Thread(target=email_scraper_worker, daemon=True)
        t.start()
        threads.append(t)
        
    print("Starting streaming from CSV...")
    with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'link' in row and str(row['link']) in processed_links:
                continue
            if 'name' in row and str(row['name']) in processed_names:
                continue
            
            if 'website' not in row:
                row['website'] = None
                
            lead_queue.put(row)
            
    # Wait for all tasks to complete
    lead_queue.join()
    
    # Send poison pill to stop workers
    for _ in range(NUM_WORKER_THREADS):
        lead_queue.put(None)
        
    for t in threads:
        t.join()
        
    print(f"\\n\\n=======================================")
    print(f"Email Scraping Complete! Results saved to {OUTPUT_CSV}")
    print("=======================================")

if __name__ == '__main__':
    main()
"""

content = content[:main_start] + new_main

with open("scraper_core/pipeline.py", "w", encoding="utf-8") as f:
    f.write(content)
print("done")
