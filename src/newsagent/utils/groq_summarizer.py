# ── src/newsagent/utils/groq_summarizer.py ────────────────────────────────
"""
summarize_long_transcript(text, api_key, model="llama-3.3-70b-versatile") → str

• Scales requested summary length dynamically (120 – 700 words).
• Retries on Groq 429 (rate-limit) and 413 (payload too large).
• Removes Groq boiler-plate lines from the result.
"""

from __future__ import annotations

import math, os, random, re, time
from typing import List

import requests

# current Groq model names (June 2025)
MODEL_DEFAULT = "llama-3.3-70b-versatile"

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
HEADERS_TPL   = {
    "Authorization": "Bearer {key}",
    "Content-Type" : "application/json",
}

_BOILER_RGX = re.compile(
    r"^\s*(summary\s*:|here\s+is\s+a\s+(?:merged|concise|brief|clear)"
    r"|in\s+clear,\s*factual\s+prose\s*:?)\s*", re.I)


# ────────────────────────── helpers ────────────────────────────────────────
def _post(payload: dict, api_key: str, retries: int = 5) -> str:
    """POST with automatic back-off for 429 and propagate 413."""
    headers = {k: v.format(key=api_key) for k, v in HEADERS_TPL.items()}
    delay = 2.0

    for attempt in range(retries):
        try:
            r = requests.post(GROQ_ENDPOINT, json=payload,
                              headers=headers, timeout=90)
            if r.status_code == 429:
                raise RuntimeError("429")
            if r.status_code == 413:
                raise RuntimeError("413")
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except RuntimeError as e:
            if str(e) == "429":                      # rate-limit
                sleep = delay * (1.5 ** attempt) + random.uniform(0, 1.5)
                print(f"   Groq 429 – retry {attempt+1}/{retries} "
                      f"(sleep {sleep:.0f}s)…")
                time.sleep(sleep)
                continue
            if str(e) == "413":                      # payload too large
                raise
            raise
    raise RuntimeError("unreachable")


def _clean(text: str) -> str:
    """Strip boiler-plate leading lines Groq sometimes adds."""
    out: List[str] = []
    for ln in text.splitlines():
        ln2 = _BOILER_RGX.sub("", ln)
        if ln2.strip():
            out.append(ln2)
    return "\n".join(out)


# ───────────────────────── main API ────────────────────────────────────────
def summarize_long_transcript(
    transcript: str,
    api_key: str | None = None,
    *,
    model: str = MODEL_DEFAULT,
    words_per_chunk: int = 80,
) -> str:
    """Split a long transcript, summarise each chunk, then merge."""
    api_key = api_key or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing")

    WORDS_PER_4K = 4000 * 4         # ≈ 16 000 words / 4 000 tokens
    words        = transcript.split()
    chunks       = [" ".join(words[i : i + WORDS_PER_4K])
                    for i in range(0, len(words), WORDS_PER_4K)]

    results: List[str] = []

    for chunk in chunks:
        while True:
            tgt_words = max(120, min(700,
                              words_per_chunk *
                              math.ceil(len(chunk.split()) / 8000 * 100)))
            system_prompt = (
                "You are a precise analyst. Summarise the following "
                f"transcript in ≈{tgt_words} words, using bullet points "
                "where helpful, and keep ALL important numbers / names / "
                "causality. Do NOT add an intro header."
            )
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",  "content": chunk},
                ],
            }
            print(f"    Summarising chunk "
                  f"{min(1, len(chunk.split()) // 4000)}/1 …")
            try:
                text = _post(payload, api_key)
                results.append(_clean(text))
                break                                   # success – next chunk
            except RuntimeError as e:
                if str(e) == "413":                     # payload too large
                    print("      413 – chunk halved, retrying…")
                    chunk = " ".join(chunk.split()[: len(chunk.split()) // 2])
                    continue
                raise                                   # other errors → abort

    # single-chunk → done
    if len(results) == 1:
        return results[0]

    # merge partial summaries into one
    merge_prompt = (
        "Merge the following PARTIAL summaries into a single, cohesive "
        "≈600-word briefing. Keep the structure concise."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": merge_prompt},
            {"role": "user",   "content": "\n\n".join(results)},
        ],
    }
    merged = _post(payload, api_key)
    return _clean(merged)
