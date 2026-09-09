import os

files_to_check = ["pipeline_executor.py", "update_pipeline.py"]
for file in files_to_check:
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Replace lead.py with lead_v2.py in run_script calls and log messages
        # We need to be careful to only replace the execution of lead.py
        new_code = code.replace("run_script('lead.py'", "run_script('lead_v2.py'")
        
        # Also replace "lead.py_completed" flags with "lead_v2.py_completed" to maintain pipeline logic
        new_code = new_code.replace('"lead.py_completed"', '"lead_v2.py_completed"')
        new_code = new_code.replace("lead.py failed", "lead_v2.py failed")
        new_code = new_code.replace("lead.py as completed", "lead_v2.py as completed")
        
        if code != new_code:
            with open(file, "w", encoding="utf-8") as f:
                f.write(new_code)
            print(f"Updated {file}")
