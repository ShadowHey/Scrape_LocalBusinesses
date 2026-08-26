import os
from dotenv import load_dotenv

load_dotenv()

IITBHU_USERNAME = os.getenv("IITBHU_USERNAME", "23114009")
IITBHU_PASSWORD = os.getenv("IITBHU_PASSWORD", "")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "20"))
FAILURE_CONFIRMATION_COUNT = int(os.getenv("FAILURE_CONFIRMATION_COUNT", "2"))
MAX_LOGIN_RETRIES = int(os.getenv("MAX_LOGIN_RETRIES", "3"))

PORTAL_URL = os.getenv("PORTAL_URL", "http://192.168.249.1/")
KEEP_BROWSER_OPEN = os.getenv("KEEP_BROWSER_OPEN", "true").lower() == "true"
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"

# Comma-separated list of Wi-Fi network names to monitor
_target_networks = os.getenv("TARGET_WIFI_NETWORKS", "IIT(BHU),Test")
TARGET_WIFI_NETWORKS = [n.strip() for n in _target_networks.split(",")]

CHROME_PROFILE_DIR = os.getenv("CHROME_PROFILE_DIR", os.path.join(os.getcwd(), "chrome_profile"))

# endpoints for checking internet
TEST_URLS = [
    "http://clients3.google.com/generate_204",
    "http://connectivitycheck.gstatic.com/generate_204"
]
