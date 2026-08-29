import time
import os
import json
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.join(BASE_DIR, 'admin')
HEALTH_JSON = os.path.join(ADMIN_DIR, 'health_profiles.json')
SAFETY_JSON = os.path.join(ADMIN_DIR, 'safety_limit.json')
STOP_FLAG = os.path.join(ADMIN_DIR, 'STOP_FLAG')
PIPELINE_PAUSED = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')

def get_profile_settings():
    desired = 10
    safety_limit = 1
    if os.path.exists(SAFETY_JSON):
        try:
            with open(SAFETY_JSON, 'r') as f:
                data = json.load(f)
                safety_limit = data.get("safety_limit", 1)
                desired = data.get("desired", 10)
        except:
            pass
    return desired, safety_limit

def get_alive_count():
    if os.path.exists(HEALTH_JSON):
        try:
            with open(HEALTH_JSON, 'r') as f:
                paths = json.load(f)
                return len(paths)
        except:
            pass
    return 0

def main():
    print("========================================")
    print("      PROFILE AUTOMATOR STARTED         ")
    print("========================================")
    print("I will run silently in the background and monitor profile health every 2.5 minutes.")
    print("If profiles drop below the safety limit, I will gracefully pause the pipeline,")
    print("renew the profiles, and then resume the pipeline automatically.\n")
    
    try:
        while True:
            desired, safety_limit = get_profile_settings()
            alive = get_alive_count()
            burned = max(0, desired - alive)
            
            print(f"[Automator] Heartbeat Check - Active: {alive} | Burned: {burned} | Safety Limit: {safety_limit}")
            
            if alive < safety_limit:
                print(f"[Automator] WARNING! Active profiles ({alive}) dropped below safety limit ({safety_limit}).")
                print("[Automator] Initiating graceful pipeline pause...")
                
                # 1. Write PIPELINE_PAUSED to prevent it from picking up a new task or looping back immediately
                with open(PIPELINE_PAUSED, 'w') as f:
                    f.write("PAUSED_BY_AUTOMATOR")
                
                # 2. Write PAUSE_AND_WAIT to STOP_FLAG to safely interrupt a currently running scraper
                with open(STOP_FLAG, 'w') as f:
                    f.write("PAUSE_AND_WAIT")
                
                print("[Automator] Waiting 15 seconds for executor to safely archive and pause...")
                time.sleep(15)
                
                print(f"[Automator] Launching Profile Manager to restore profiles up to {desired}...")
                pm_process = subprocess.run([sys.executable, os.path.join("scraper_core", "profile_manager.py"), "--auto", str(desired), "--limit", str(safety_limit)])
                
                if pm_process.returncode == 0:
                    print("[Automator] Profiles successfully generated!")
                else:
                    print("[Automator] Profile Manager encountered an issue, but continuing...")
                
                print("[Automator] Resuming pipeline executor...")
                if os.path.exists(PIPELINE_PAUSED):
                    try: os.remove(PIPELINE_PAUSED)
                    except: pass
                
                if os.path.exists(STOP_FLAG):
                    try: os.remove(STOP_FLAG)
                    except: pass
                
                print("[Automator] Pipeline resumed. Back to monitoring.")
            
            # Sleep 2.5 minutes (150 seconds)
            time.sleep(150)
            
    except KeyboardInterrupt:
        print("\n[Automator] Ctrl+C detected. Shutting down gracefully.")

if __name__ == "__main__":
    main()
