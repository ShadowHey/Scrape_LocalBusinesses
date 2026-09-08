import re

with open("scraper_core/lead_v2.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Remove the Watchdog definition and thread start
watchdog_pattern = re.compile(
    r"\s*start_time_ref\s*=\s*\[None\].*?watchdog_thread\.start\(\)\n",
    re.DOTALL
)
code = watchdog_pattern.sub("\n", code)

# 2. Remove context_ref and start_time_ref updates
code = re.sub(r"\s*context_ref\[0\]\s*=\s*context\n", "\n", code)
code = re.sub(r"\s*start_time_ref\[0\]\s*=\s*(?:time\.time\(\)|None)\n", "\n", code)

# 3. Increase timeout for CSV download in open_popup_and_crawl
code = code.replace("expect_download(timeout=30_000)", "expect_download(timeout=90_000)")

with open("scraper_core/lead_v2.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patch applied to lead_v2.py")
