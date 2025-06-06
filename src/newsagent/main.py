# ── src/newsagent/main.py ────────────────────────────────────────────────
"""
NewsAgent main entry

• Collect → summarise (Groq) → write English Markdown.
• Auto-translate to any language whose RECIP_xx is present in .env
  (DE / SV / PL supported).
• Mails each language version to its bucket.

CLI
  --channels   custom channels.json  (default: data/channels.json)
  --threads    Groq workers          (forced to 1 for free tier)
  --max-chunks trim transcripts
  --max-bytes  skip big vids
  --fast       = threads 1, chunks 10
"""

from __future__ import annotations
import argparse, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
load_dotenv()

from src.newsagent.collectors.youtube_collector import collect_youtube
from src.newsagent.utils.groq_summarizer        import summarize_long_transcript
from src.newsagent.utils.report_writer          import write_markdown_report
from src.newsagent.utils.email_sender           import send_report_via_email
from src.newsagent.utils.translator             import translate
from src.newsagent.utils.debug_tools            import log_run_summary


# ── CLI helpers ──────────────────────────────────────────────────────────
def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser("newsagent")
    p.add_argument("--channels",   type=Path,
                   help="Custom channels.json (default: data/channels.json)")
    p.add_argument("--threads",    type=int, default=1,
                   help="Groq workers (keep 1 for free tier)")
    p.add_argument("--max-chunks", type=int, default=None,
                   help="Trim every transcript to N chunks")
    p.add_argument("--max-bytes",  type=int, default=None,
                   help="Skip transcripts larger than N bytes")
    p.add_argument("--fast", action="store_true",
                   help="Shortcut = --threads 1 --max-chunks 10")
    return p.parse_args()


def _trim(videos: List[Dict], max_chunks: int | None,
          max_bytes: int | None) -> List[Dict]:
    if not max_chunks and not max_bytes:
        return videos

    def _one(v: Dict) -> Dict | None:
        txt = v["transcript"]
        if max_bytes and len(txt.encode()) > max_bytes:
            return None
        if max_chunks:
            words = txt.split()
            v["transcript"] = " ".join(words[: max_chunks * 400])
        return v

    return [t for v in videos if (t := _one(v))]


# ── main ─────────────────────────────────────────────────────────────────
def main() -> None:
    args = _cli()

    if args.fast:
        args.threads, args.max_chunks = 1, 10
        print("[INFO] fast-mode → threads=1  max_chunks=10")

    if args.threads != 1:
        print("[WARN] forcing --threads 1 (Groq free tier)")
        args.threads = 1

    if not os.getenv("GROQ_API_KEY"):
        sys.exit("❌  GROQ_API_KEY missing")

    base_dir     = Path(__file__).resolve().parents[2]
    channel_file = args.channels or base_dir / "data" / "channels.json"

    # 1) collect -----------------------------------------------------------
    videos = collect_youtube(channel_file)
    videos = _trim(videos, args.max_chunks, args.max_bytes)

    # 2) summarise ---------------------------------------------------------
    print("\n▶  Summarising …")
    t0 = time.time()

    grouped: Dict[str, List[Dict]] = {}
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut2vid = {pool.submit(summarize_long_transcript, v["transcript"]): v
                   for v in videos}
        for fut in as_completed(fut2vid):
            vid = fut2vid[fut]
            try:
                vid["summary"] = fut.result()
            except Exception as exc:
                vid["summary"] = f"[ERROR] Groq summarisation failed: {exc}"
            grouped.setdefault(vid["topic"], []).append(vid)

    print(f"[INFO] Summaries ready in {time.time()-t0:,.0f}s")

    # 3) debug log ---------------------------------------------------------
    flat = [v for vs in grouped.values() for v in vs]
    log_run_summary(flat, Path("reports/debug_transcripts.json"))

    # 4) English report ----------------------------------------------------
    report_en = write_markdown_report(grouped)
    print(f"[INFO] EN report → {report_en}")

    send_mail = os.getenv("SEND_EMAIL", "0") == "1"
    if send_mail:
        send_report_via_email(report_en)

    # 5) extra languages ---------------------------------------------------
    lang_cfg = {                      # suffix : (Groq-tag , env name)
        "de": ("DEU", "RECIP_DE"),
        "sv": ("SWE", "RECIP_SV"),
        "pl": ("POL", "RECIP_PL"),
    }

    md_en = report_en.read_text(encoding="utf-8")
    ts    = report_en.stem.split("_", 2)[2]           # timestamp part
    out_dir = report_en.parent

    for sfx, (tag, env_name) in lang_cfg.items():
        if not os.getenv(env_name):                   # skip if no recipient
            continue
        out_path = out_dir / f"daily_summary_{ts}_{sfx}.md"
        translated = translate(md_en, tag)
        out_path.write_text(translated, encoding="utf-8")
        print(f"[INFO] {tag} report → {out_path}")
        if send_mail:
            send_report_via_email(out_path)


if __name__ == "__main__":
    main()
