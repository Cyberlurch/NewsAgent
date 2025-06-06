# ── src/newsagent/utils/translator.py ────────────────────────────────
"""
translate(text, lang) → str

• Returns the input unchanged for ENG, otherwise translates & caches.
• Automatically splits long documents to avoid Groq 413 limits.
• Uses the new Groq model aliases (llama-3.1-8b-instant).
• Accepts either ISO-639-2 codes (DEU, SWE, POL …) **or**
  the short “de / sv / pl” forms – they’re normalised internally.
"""

from __future__ import annotations
import hashlib, json, os, random, re, time
from pathlib import Path
from typing import Dict, List

import requests

# ── persistent cache ────────────────────────────────────────────────
CACHE_DIR = Path(__file__).resolve().parents[2] / "cache" / "translate"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cache_key(txt: str, lang: str) -> Path:
    h = hashlib.sha256(f"{lang}::{txt}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{lang}_{h}.json"

def _cached(txt: str, lang: str) -> str | None:
    fp = _cache_key(txt, lang)
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))["t"]
    return None

def _save(txt: str, lang: str, out: str) -> None:
    _cache_key(txt, lang).write_text(json.dumps({"t": out}), encoding="utf-8")

# ── Groq client helpers ─────────────────────────────────────────────
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODEL         = "llama-3.1-8b-instant"
_BOILER       = re.compile(r"^\s*(translation\s*:)", re.I)

def _post(payload: Dict, api_key: str) -> requests.Response:
    return requests.post(
        GROQ_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )

# ISO-639-1/2 normalisation ---------------------------------------------------
_LANG_MAP = {
    "EN": "ENG", "ENG": "ENG",
    "DE": "DEU", "DEU": "DEU",
    "SV": "SWE", "SV_SE": "SWE", "SWE": "SWE",  # Swedish  ← fixed
    "PL": "POL", "POL": "POL",
}

def _norm(lang: str) -> str:
    key = lang.upper().replace("-", "_")
    return _LANG_MAP.get(key, lang.upper())

# ── public API ───────────────────────────────────────────────────────
def translate(text: str, lang: str) -> str:
    """
    ENG → passthrough, else translate using Groq with exponential back-off.
    Splits long markdown into ~3000-char chunks if Groq returns 413.
    """
    lang = _norm(lang)
    if lang == "ENG":
        return text

    if cached := _cached(text, lang):
        return cached

    api_key = os.getenv("GROQ_API_KEY") or ""
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing")

    # --- inner helper ------------------------------------------------------
    def _translate_chunk(chunk: str) -> str:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system",
                 "content": (f"Translate the following GitHub-flavoured "
                             f"Markdown into **{lang}**. Preserve formatting, "
                             "DO NOT add a preface or a footer.")},
                {"role": "user", "content": chunk},
            ],
        }

        delay = 2.0
        for attempt in range(8):
            r = _post(payload, api_key)
            if r.status_code == 429:
                sleep = delay * (1.6 ** attempt) + random.uniform(0, 1.3)
                print(f"    Groq 429 while translating – sleep {sleep:.1f}s …")
                time.sleep(sleep)
                continue
            if r.status_code == 413:
                raise RuntimeError("413")
            r.raise_for_status()
            out = r.json()["choices"][0]["message"]["content"]
            return _BOILER.sub("", out).lstrip()

        raise RuntimeError("translation: too many retries")

    # --- try whole text first ---------------------------------------------
    try:
        out = _translate_chunk(text)
    except RuntimeError as e:
        if str(e) != "413":
            raise
        # need to chunk -----------------------------------------------------
        print("[WARN] Text too long → chunking …")
        parts: List[str] = []
        buf = []
        words = text.split()
        for w in words:
            buf.append(w)
            if sum(len(x) for x in buf) > 3000:
                parts.append(" ".join(buf))
                buf = []
        if buf:
            parts.append(" ".join(buf))

        translated_chunks = []
        for i, chunk in enumerate(parts, 1):
            print(f"    Translating chunk {i}/{len(parts)} …")
            translated_chunks.append(_translate_chunk(chunk))
        out = "\n\n".join(translated_chunks)

    _save(text, lang, out)
    return out
