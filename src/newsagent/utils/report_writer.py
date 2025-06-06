# ── src/newsagent/utils/report_writer.py ──────────────────────────────────
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import markdown

def write_markdown_report(grouped: Dict[str, List[Dict]]) -> Path:
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = Path(__file__).resolve().parents[2] / "reports"
    out_dir.mkdir(exist_ok=True)

    md = [f"# Daily Summary – {now.replace('_', ' ')}\n"]

    for topic, videos in grouped.items():
        md.append(f"\n\n## {topic.upper()}")
        for v in videos:
            if not all(k in v for k in ("title", "summary")):
                continue        # require only what we truly need

            url = v.get("url") or (
                f"https://www.youtube.com/watch?v={v['id']}" if "id" in v else "#"
            )
            md.append(f"\n### [{v['title']}]({url})")
            if "channel" in v:
                md.append(f"*{v['channel']}*  \n")
            md.append(v["summary"])
            md.append("\n")

    path = out_dir / f"daily_summary_{now}.md"
    path.write_text("\n".join(md), encoding="utf-8")
    return path

def convert_markdown_to_html(md_text: str) -> str:
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body {{font-family: Arial, sans-serif; max-width: 800px; margin:auto}}
pre {{background:#f0f0f0; padding:.5em; overflow-x:auto}}
</style></head><body>{html}</body></html>"""
