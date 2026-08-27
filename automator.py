import time
import subprocess
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.join(BASE_DIR, 'admin')
NEEDS_PROFILES_FLAG = os.path.join(ADMIN_DIR, 'NEEDS_PROFILES_FLAG')
PIPELINE_PAUSED = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')

def get_profile_settings():
    desired = 10
    safety_limit = 1
    try:
        with open(os.path.join(ADMIN_DIR, 'safety_limit.json'), 'r') as f:
            data = json.load(f)
            safety_limit = data.get("safety_limit", 1)
            desired = data.get("desired", 10)
    except:
        pass
    return desired, safety_limit

def main():
    print("========================================")
    print("      PROFILE AUTOMATOR STARTED         ")
    print("========================================")
    print("I will run silently in the background and watch for profile shortages.")
    print("You can run pipeline_executor.py manually in a separate window as usual.\n")
    
    try:
        while True:
            # Simply check if the pipeline requested more profiles
            if os.path.exists(NEEDS_PROFILES_FLAG):
                print("[Automator] Detected profile shortage! Regenerating profiles...")
                
                # Immediately remove the flag so we don't trigger this again while building
                try:
                    os.remove(NEEDS_PROFILES_FLAG)
                except: pass
                
                desired, safety_limit = get_profile_settings()
                print(f"[Automator] Running profile_manager.py --auto {desired} --limit {safety_limit}")
                
                # Run profile_manager autonomously
                pm_process = subprocess.run([sys.executable, os.path.join("scraper_core", "profile_manager.py"), "--auto", str(desired), "--limit", str(safety_limit)])
                
                if pm_process.returncode == 0:
                    print("[Automator] Profiles generated successfully.")
                    print("[Automator] Removing global pause flag to wake up the executor...")
                    if os.path.exists(PIPELINE_PAUSED):
                        try:
                            os.remove(PIPELINE_PAUSED)
                        except: pass
                    print("[Automator] Done. Back to watching.")
                else:
                    print("[Automator] Error generating profiles. Stopping automator.")
                    break
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n[Automator] Ctrl+C detected. Shutting down gracefully.")

if __name__ == "__main__":
    main()
