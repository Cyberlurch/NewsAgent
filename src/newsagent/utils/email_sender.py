# ── src/newsagent/utils/email_sender.py ───────────────────────────────
from __future__ import annotations
import os, smtplib
from email.message import EmailMessage
from pathlib import Path
from src.newsagent.utils.report_writer import convert_markdown_to_html
from src.newsagent.utils.translator    import translate

_LANG_TAG = {"de": "DEU", "sv": "SWE", "pl": "POL"}   # ← fixed “SWE”

def _lang_from_stem(stem: str) -> str:
    parts = stem.split("_")
    return parts[-1].lower() if len(parts[-1]) == 2 else "en"

def send_report_via_email(md_path: Path | str) -> None:
    md_path = Path(md_path)
    raw_en  = md_path.read_text(encoding="utf-8")
    lang2   = _lang_from_stem(md_path.stem)

    # --- translate if needed ---------------------------------------------
    md_body = translate(raw_en, _LANG_TAG.get(lang2, "ENG"))

    recip = (os.getenv(f"RECIP_{lang2.upper()}") or
             os.getenv("EMAIL_TO")                or
             os.getenv("RECIP_EN"))
    if not recip:
        print(f"[WARN] No recipient for language “{lang2}” – skipped.")
        return

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    pwd  = os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD", "")
    if not all((host, user, pwd)):
        print("[WARN] SMTP credentials missing – mail skipped")
        return

    html_body = convert_markdown_to_html(md_body)

    msg            = EmailMessage()
    msg["Subject"] = md_path.stem.replace("_", " ").title()
    msg["From"]    = os.getenv("EMAIL_FROM") or user
    msg["To"]      = recip
    msg.set_content(html_body, subtype="html", charset="utf-8")
    msg.add_attachment(raw_en.encode("utf-8"),
                       maintype="text", subtype="markdown",
                       filename=md_path.name)

    print(f"[INFO] mailing {md_path.name} → {recip}")
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, pwd)
        smtp.send_message(msg)
    print("[OK] sent.")
