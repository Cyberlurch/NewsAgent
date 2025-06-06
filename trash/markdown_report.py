# src/newsagent/utils/markdown_report.py

import os
from datetime import datetime

def save_markdown_report(content, base_dir=None):
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    report_dir = os.path.join(base_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"report_{timestamp}.md"
    filepath = os.path.join(report_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n[INFO] Markdown report saved to: {filepath}\n")
