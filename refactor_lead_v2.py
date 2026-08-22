import os
import re
import shutil

ORIGINAL_LEAD = r"C:\Users\DhruvBisht\Desktop\OriginalScraperUpdatedCopy_Test\lead.py"
TARGET_LEAD = r"C:\Users\DhruvBisht\Desktop\Firecrawl\scraper_core\lead.py"

# Start fresh from original
shutil.copy(ORIGINAL_LEAD, TARGET_LEAD)

with open(TARGET_LEAD, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start of the config (search_terms =) and the end (where zip_codes block ends)
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line.startswith('search_terms = ['):
        start_idx = i
    if line.startswith('def discover_extension('):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_config = """
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'current_task_config.json')
try:
    with open(CONFIG_PATH, 'r') as f:
        _cfg = json.load(f)
        search_terms = _cfg.get("search_terms", [])
        locality_label = _cfg.get("locality", "Unknown")
        zip_codes = _cfg.get("zip_codes", [])
except Exception as e:
    print(f"Warning: Could not load task config: {e}")
    search_terms = []
    locality_label = ""
    zip_codes = []

"""
    new_lines = lines[:start_idx] + [new_config] + lines[end_idx:]
    final_content = "".join(new_lines)
    
    # Replace main_orchestrator
    orchestrator_match = re.search(r'def main_orchestrator\(\):.*', final_content, re.DOTALL)
    if orchestrator_match:
        run_func = """
def run():
    print(f"Launching Orchestrator for {len(search_terms)} terms across {len(zip_codes)} zip codes in {locality_label}")
    import multiprocessing
    import json
    import os
    import re
    
    # Load healthy profiles
    healthy_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'health_profiles.json')
    healthy_idx = []
    if os.path.exists(healthy_json):
        try:
            with open(healthy_json, 'r') as f:
                paths = json.load(f)
                for p in paths:
                    # Extract the number from ChromeUserDataX
                    m = re.search(r'ChromeUserData(\d+)', p)
                    if m:
                        healthy_idx.append(int(m.group(1)))
        except Exception as e:
            print(f"Failed to load healthy profiles: {e}")
            
    if not healthy_idx:
        print("[!] No healthy profiles found. Defaulting to 1.")
        healthy_idx = [1]
        
    num_profiles = len(healthy_idx)
    
    # Process in batches equal to number of available healthy profiles
    for i in range(0, len(search_terms), num_profiles):
        batch = search_terms[i:i+num_profiles]
        print(f"\\n=======================================================")
        print(f"Starting Batch {i//num_profiles + 1} with terms: {batch}")
        print(f"=======================================================")
        
        processes = []
        for j, term in enumerate(batch):
            profile_idx = healthy_idx[j % num_profiles]
            p = multiprocessing.Process(target=worker, args=(profile_idx, term))
            processes.append(p)
            p.start()
            
        for p in processes:
            p.join()
            
    print("\\nAll map scraping complete!")

if __name__ == '__main__':
    run()
"""
        final_content = final_content[:orchestrator_match.start()] + run_func
        
    with open(TARGET_LEAD, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print("Successfully rebuilt lead.py with helpers and healthy profile mapping.")
else:
    print("Could not find start/end indices")
