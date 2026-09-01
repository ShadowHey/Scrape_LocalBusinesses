import os
import shutil

base_dir = r"C:\Users\DhruvBisht\Desktop\Firecrawl"
target_dir = os.path.join(base_dir, "Logs_NewRuns", "WeddingAgency_Texas_01Sep26_1151")

for folder in ["pre_segment_csvs", "uploadable_csvs"]:
    src = os.path.join(base_dir, folder)
    if os.path.exists(src):
        dst = os.path.join(target_dir, folder)
        try:
            shutil.move(src, dst)
            print(f"Moved {folder} to {dst}")
        except Exception as e:
            print(f"Error moving {folder}: {e}")
