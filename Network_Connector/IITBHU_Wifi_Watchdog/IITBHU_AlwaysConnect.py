import os
import sys
import subprocess
import time
import argparse

# Setup environment variables path before importing anything else
if getattr(sys, 'frozen', False):
    # Running as Pyinstaller bundle
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(app_dir, '.env')

def setup_credentials():
    print("==================================================")
    print("   IIT(BHU) Wi-Fi Watchdog - Auto-Connect")
    print("==================================================")
    
    existing_user = ""
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("IITBHU_USERNAME="):
                    val = line.strip().split("=", 1)[1]
                    if val != "23114009" and val != "":
                        existing_user = val
                    
    print(f"\nCurrent Username: {existing_user if existing_user else 'Not set'}")
    print("Leave blank and press Enter to keep existing credentials.\n")
    
    user = input("Enter IIT(BHU) Username: ").strip()
    pwd = input("Enter IIT(BHU) Password: ").strip()
    
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    env_vars[k] = v
                    
    if user: env_vars["IITBHU_USERNAME"] = user
    if pwd: env_vars["IITBHU_PASSWORD"] = pwd
    
    if "CHECK_INTERVAL" not in env_vars: env_vars["CHECK_INTERVAL"] = "20"
    if "FAILURE_CONFIRMATION_COUNT" not in env_vars: env_vars["FAILURE_CONFIRMATION_COUNT"] = "2"
    if "MAX_LOGIN_RETRIES" not in env_vars: env_vars["MAX_LOGIN_RETRIES"] = "3"
    if "PORTAL_URL" not in env_vars: env_vars["PORTAL_URL"] = "http://192.168.249.1/"
    if "KEEP_BROWSER_OPEN" not in env_vars: env_vars["KEEP_BROWSER_OPEN"] = "true"
    if "HEADLESS_MODE" not in env_vars: env_vars["HEADLESS_MODE"] = "true"
    if "TARGET_WIFI_NETWORKS" not in env_vars: env_vars["TARGET_WIFI_NETWORKS"] = "IIT(BHU),Test"
    
    with open(env_path, "w") as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")
            
    print("\nCredentials saved successfully!")

def kill_existing():
    current_pid = os.getpid()
    exe_name = os.path.basename(sys.executable)
    
    # Also if running as python script, kill python instances with same name
    target_names = [exe_name]
    if not getattr(sys, 'frozen', False):
        target_names = ["python.exe", "pythonw.exe", "IITBHU_Watchdog.exe"]
        
    try:
        for target in target_names:
            output = subprocess.check_output(["tasklist", "/FI", f"IMAGENAME eq {target}", "/FO", "CSV"], text=True)
            for line in output.splitlines():
                if target in line:
                    parts = line.split('","')
                    if len(parts) > 1:
                        pid = int(parts[1].replace('"', ''))
                        if pid != current_pid:
                            # Try to kill it safely
                            subprocess.call(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def install_browsers():
    print("\nEnsuring background browsers are ready...")
    try:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(app_dir, "pw-browsers")
        
        import playwright._impl._driver
        driver_executable = playwright._impl._driver.compute_driver_executable()
        env = playwright._impl._driver.get_driver_env()
        
        # We redirect stdout so it doesn't spam unless it's downloading
        subprocess.run([driver_executable, "install", "chromium"], env=env, check=True)
        print("Browsers ready.")
    except Exception as e:
        print(f"Error checking browsers: {e}")

def run_background():
    exe_path = sys.executable
    print("\nStarting background watchdog service...")
    
    if getattr(sys, 'frozen', False):
        subprocess.Popen([exe_path, "--daemon"], creationflags=subprocess.CREATE_NO_WINDOW, cwd=app_dir)
    else:
        # Run using pythonw.exe if not frozen
        pythonw_path = exe_path.replace("python.exe", "pythonw.exe")
        subprocess.Popen([pythonw_path, sys.argv[0], "--daemon"], creationflags=subprocess.CREATE_NO_WINDOW, cwd=app_dir)
        
    print("Service is now RUNNING IN THE BACKGROUND!")
    print("It will silently connect to Wi-Fi whenever required.")
    
    # Add to startup automatically
    add_to_startup()
    
    print("\nYou can safely close this window.")
    time.sleep(3)
    
def add_to_startup():
    print("Adding shortcut to Windows Startup folder...")
    import winreg
    
    exe_path = sys.executable
    if not getattr(sys, 'frozen', False):
        return # Skip adding to startup if it's not the final EXE
        
    try:
        startup_folder = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        shortcut_path = os.path.join(startup_folder, "IITBHU_AlwaysConnect.vbs")
        
        # We write a tiny VBS to launch the EXE silently, just to be extremely safe, 
        # though the EXE itself when run without arguments opens the setup console.
        # Wait, if the EXE is run from startup without args, it opens the console.
        # We need it to run WITH --daemon on startup!
        
        with open(shortcut_path, "w") as f:
            f.write(f'Set oShell = CreateObject ("Wscript.Shell")\n')
            f.write(f'Dim strArgs\n')
            f.write(f'strArgs = "cmd /c """" & "{exe_path}" & """ --daemon"\n')
            f.write(f'oShell.Run strArgs, 0, false\n')
    except Exception as e:
        print(f"Failed to add to startup: {e}")

def daemon_mode():
    # Redirect stdout and stderr to prevent OSError on logging due to missing console
    f = open(os.devnull, 'w')
    sys.stdout = f
    sys.stderr = f
    
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(app_dir, "pw-browsers")
    
    # Force reload environment
    import config
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path, override=True)
    
    config.IITBHU_USERNAME = os.environ.get("IITBHU_USERNAME")
    config.IITBHU_PASSWORD = os.environ.get("IITBHU_PASSWORD")
    config.CHROME_PROFILE_DIR = os.path.join(app_dir, "chrome_profile")
    
    # Strip --daemon from sys.argv so main.py's argparse doesn't crash on unrecognized argument
    if "--daemon" in sys.argv:
        sys.argv.remove("--daemon")
    
    # Start the watchdog
    import main
    main.main()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()
    
    if args.daemon:
        daemon_mode()
    else:
        kill_existing()
        setup_credentials()
        install_browsers()
        run_background()
