import os
import re

LEAD_PY = r"C:\Users\DhruvBisht\Desktop\Firecrawl\scraper_core\lead.py"

with open(LEAD_PY, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We know the config block is between lines 16 and 850ish.
# We will look for "search_terms = [" and "locality_label = " and "zip_codes={"
# Actually, the simplest is to replace the chunk from "search_terms =" to the end of zip_codes.

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith('search_terms = ['):
        start_idx = i
    if line.strip() == '76934",':  # we saw this at line 850
        pass

# Let's just find "search_terms =" and the next "def worker"
for i, line in enumerate(lines):
    if line.startswith('search_terms = ['):
        start_idx = i
    if line.startswith('def worker('):
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

PROPERTY_ZIPS = {} # Not used directly if we just pass zip_codes

"""
    new_lines = lines[:start_idx] + [new_config] + lines[end_idx:]
    
    # Also replace main_orchestrator
    final_content = "".join(new_lines)
    
    # Remove the subprocess calls at the bottom of main_orchestrator
    # We'll just replace the whole main_orchestrator block
    orchestrator_match = re.search(r'def main_orchestrator\(\):.*', final_content, re.DOTALL)
    if orchestrator_match:
        final_content = final_content[:orchestrator_match.start()] + """
def run():
    print(f"Launching Orchestrator for {len(search_terms)} terms across {len(zip_codes)} zip codes in {locality_label}")
    import multiprocessing
    # Process in batches of up to 5 terms
    for i in range(0, len(search_terms), 5):
        batch = search_terms[i:i+5]
        print(f"\\n=======================================================")
        print(f"Starting Batch {i//5 + 1} with terms: {batch}")
        print(f"=======================================================")
        
        processes = []
        for profile_idx, term in enumerate(batch, start=6):
            p = multiprocessing.Process(target=worker, args=(profile_idx, term))
            processes.append(p)
            p.start()
            
        for p in processes:
            p.join()
            
    print("\\nAll map scraping complete!")

if __name__ == '__main__':
    run()
"""
    
    with open(LEAD_PY, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print("Successfully refactored lead.py")
else:
    print(f"Could not find indices. start: {start_idx}, end: {end_idx}")

