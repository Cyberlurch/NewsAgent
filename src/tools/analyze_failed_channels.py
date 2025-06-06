# ── src/tools/analyze_failed_channels.py ──────────────────────────────────────
"""
Analyze a debug_transcripts.json file and identify:
- Channels that fail consistently
- Their status counts
- Recommendations for skipping or manual inspection
"""

import json
from collections import defaultdict, Counter
from pathlib import Path

DEBUG_FILE = Path("reports/debug_transcripts.json")
OUTPUT_FILE = Path("reports/channel_failure_report.txt")

def load_debug_log(file_path: Path):
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)

def analyze(log):
    channel_stats = defaultdict(lambda: Counter({"ok": 0, "error": 0}))
    
    for item in log:
        ch = item["channel"]
        status = item["status"]
        if status.startswith("ok"):
            channel_stats[ch]["ok"] += 1
       
