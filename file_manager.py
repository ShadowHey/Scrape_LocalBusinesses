import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'Logs_NewRuns')

def get_possible_files():
    return [
        "Emails_Fetched.csv",
        "FinalEmails.csv", 
        "Final_Cleaned_Leads.csv", 
        "Final_Pure_Emails.csv",
        "Scraped_Phones.csv"
    ]

def archive_task(task, is_paused=False, is_error=False):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    search_terms = task.get('search_terms', ['Unknown'])
    primary_term = search_terms[0].replace(' ', '')
    locality = task.get('locality', 'Unknown').replace(' ', '')
    
    date_str = datetime.now().strftime("%d%b%y_%H%M")
    
    if is_error:
        folder_name = f"{primary_term}_{locality}_{date_str}_ERROR_{task['id']}"
    elif is_paused:
        folder_name = f"{primary_term}_{locality}_{date_str}_PAUSED_{task['id']}"
    else:
        folder_name = f"{primary_term}_{locality}_{date_str}"
        
    target_dir = os.path.join(LOGS_DIR, folder_name)
    
    final_files_dir = os.path.join(target_dir, "final_files")
    aggregated_results_dir = os.path.join(target_dir, "aggregated_results")
    
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(final_files_dir, exist_ok=True)
    os.makedirs(aggregated_results_dir, exist_ok=True)
    
    # 1. Move temp_csvs folder entirely
    temp_csvs_src = os.path.join(BASE_DIR, "temp_csvs")
    if os.path.exists(temp_csvs_src):
        try:
            shutil.move(temp_csvs_src, os.path.join(target_dir, "temp_csvs"))
        except Exception as e:
            print(f"Error moving temp_csvs: {e}")
            
    # 2. Move aggregated_leads.xlsx to aggregated_results/
    final_results_src = os.path.join(BASE_DIR, "final_results")
    if os.path.exists(final_results_src):
        try:
            for item in os.listdir(final_results_src):
                shutil.move(os.path.join(final_results_src, item), os.path.join(aggregated_results_dir, item))
            os.rmdir(final_results_src)
        except Exception as e:
            print(f"Error moving final_results: {e}")
            
    # 3. Move all generated output files to final_files/
    possible_files = get_possible_files()
    
    for f in possible_files:
        src = os.path.join(BASE_DIR, f)
        if os.path.exists(src):
            try:
                shutil.move(src, os.path.join(final_files_dir, f))
            except Exception as e:
                print(f"Error moving {f}: {e}")
                
    # 3.5 Move segmentation folders
    for seg_folder in ["pre_segment_csvs", "uploadable_csvs"]:
        src_folder = os.path.join(BASE_DIR, seg_folder)
        if os.path.exists(src_folder):
            try:
                shutil.move(src_folder, os.path.join(target_dir, seg_folder))
            except Exception as e:
                print(f"Error moving {seg_folder}: {e}")

    # 4. If this is a pause, copy the global history.json state to this folder so we can inspect it or restore it
    history_json = os.path.join(BASE_DIR, "admin", "history.json")
    if os.path.exists(history_json):
        shutil.copy2(history_json, os.path.join(target_dir, "history.json"))
        
    # 5. Drop the self-destructing batch script into the archive
    bat_src = os.path.join(BASE_DIR, "change_campaign_date.bat")
    if os.path.exists(bat_src):
        shutil.copy2(bat_src, os.path.join(target_dir, "change_campaign_date.bat"))
        
    status_str = "PAUSED" if is_paused else "completed"
    print(f"\\n[+] Task artifacts archived successfully to {folder_name}/ ({status_str})")

def restore_task(task):
    """Restores a paused task's files back to the root directory for resumption."""
    if not os.path.exists(LOGS_DIR):
        return
        
    target_id = task['id']
    paused_folder = None
    
    # Find the folder ending with _PAUSED_{target_id}
    for item in os.listdir(LOGS_DIR):
        if item.endswith(f"_PAUSED_{target_id}"):
            paused_folder = os.path.join(LOGS_DIR, item)
            break
            
    if not paused_folder:
        return # No paused state found
        
    print(f"\\n[*] Found archived paused state for Task {target_id}. Restoring files...")
    
    # 1. Restore temp_csvs
    archived_temp = os.path.join(paused_folder, "temp_csvs")
    if os.path.exists(archived_temp):
        shutil.move(archived_temp, os.path.join(BASE_DIR, "temp_csvs"))
        
    # 2. Restore aggregated_results to final_results
    archived_agg = os.path.join(paused_folder, "aggregated_results")
    if os.path.exists(archived_agg):
        final_results_dir = os.path.join(BASE_DIR, "final_results")
        os.makedirs(final_results_dir, exist_ok=True)
        for item in os.listdir(archived_agg):
            shutil.move(os.path.join(archived_agg, item), os.path.join(final_results_dir, item))
            
    # 3. Restore root CSVs
    archived_finals = os.path.join(paused_folder, "final_files")
    if os.path.exists(archived_finals):
        for f in get_possible_files():
            archived_f = os.path.join(archived_finals, f)
            if os.path.exists(archived_f):
                shutil.move(archived_f, os.path.join(BASE_DIR, f))
                
    # 3.5 Restore segmentation folders
    for seg_folder in ["pre_segment_csvs", "uploadable_csvs"]:
        archived_seg = os.path.join(paused_folder, seg_folder)
        if os.path.exists(archived_seg):
            try:
                shutil.move(archived_seg, os.path.join(BASE_DIR, seg_folder))
            except Exception as e:
                print(f"Error restoring {seg_folder}: {e}")

    # We do NOT restore history.json globally because admin/history.json is the global truth.
    # The copy inside the paused folder was just a backup snippet.
    
    # Clean up the paused folder
    try:
        shutil.rmtree(paused_folder)
        print(f"[+] Paused state restored successfully. Removed archive folder.")
    except Exception as e:
        print(f"[-] Could not remove archived folder: {e}")
