# ── src/newsagent/utils/debug_tools.py ────────────────────────────────────────
"""
log_run_summary(videos, out_path) → None

Creates a structured debug log (JSON) with:
• title, url, channel, topic, transcript length
• summary status (success/error)
• whether transcript was loaded from cache
"""

import json
from pathlib import Path
from typing import List, Dict


def log_run_summary(videos: List[Dict], out_path: Path) -> None:
    log = []
    for v in videos:
        summary = v.get("summary", "")
        if not summary:
            status = "no summary"
        elif "[ERROR]" in summary:
            status = summary.strip()
        else:
            status = f"ok ({len(summary.split())} words)"

        log.append({
            "title"     : v.get("title"),
            "url"       : v.get("url"),
            "channel"   : v.get("channel"),
            "topic"     : v.get("topic"),
            "words"     : len(v.get("transcript", "").split()),
            "status"    : status,
            "cached"    : len(v.get("transcript", "")) > 0,
        })

    debug_path = out_path.with_name("debug_transcripts.json")
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Debug log saved to {debug_path}")
