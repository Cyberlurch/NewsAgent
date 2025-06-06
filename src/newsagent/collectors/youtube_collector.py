# ── src/newsagent/collectors/youtube_collector.py ───────────────────────────
"""
Return a *flat list* of video-dicts
[{channel | title | url | transcript | topic}, …]
Transcripts are cached in   src/cache/<video-id>.txt
"""

from __future__ import annotations
import json, os, re, time, requests, yt_dlp
from pathlib import Path
from typing import Dict, List, Tuple

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
CACHE_DIR.mkdir(exist_ok=True)

try:
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
except ImportError:
    YouTubeTranscriptApi = None                              # handled later


# ── helpers ────────────────────────────────────────────────────────────────
def _load_channel_list(path: str | Path) -> Tuple[Dict[str, Dict], int]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    max_v = data.get("max_videos", 2)
    topics = {}
    for topic, lst in data.items():
        if topic == "max_videos":
            continue
        for d in lst:
            topics[d["name"]] = dict(
                url=f"https://www.youtube.com/@{d['handle']}",
                topic=topic,
            )
    return topics, max_v


def _cache_path(video_id: str) -> Path:
    return CACHE_DIR / f"{video_id}.txt"


def _clean_xml(txt: str) -> str:
    return re.sub(r"<[^>]+>", "", txt)


def _api_transcript(vid: str, max_wait: int = 12) -> str:
    if not YouTubeTranscriptApi:
        raise RuntimeError("youtube_transcript_api not installed")

    start = time.time()
    while time.time() - start < max_wait:
        try:
            segs = YouTubeTranscriptApi.get_transcript(vid, languages=["en"])
            return " ".join(s["text"] for s in segs)
        except Exception:
            time.sleep(1)
    raise TimeoutError("YT transcript API timed-out")


def _subs_transcript(info: dict, max_wait: int = 12) -> str:
    subs = info.get("subtitles") or info.get("automatic_captions")
    if subs and "en" in subs:
        url = subs["en"][0]["url"]
        try:
            r = requests.get(url, timeout=max_wait)
            r.raise_for_status()
            return _clean_xml(r.text)
        except Exception:
            pass
    return info.get("description", "")


def _get_transcript(vid: str, info: dict) -> str:
    try:
        return _api_transcript(vid)
    except Exception:
        return _subs_transcript(info)


# ── main collector ─────────────────────────────────────────────────────────
def collect_youtube(channel_list_path: str | Path) -> List[Dict]:
    channels, max_videos = _load_channel_list(channel_list_path)
    print(f"Loaded {len(channels)} channels in "
          f"{len({c['topic'] for c in channels.values()})} topic-buckets\n")

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "cachedir": str(CACHE_DIR / "yt-dlp"),      # let yt-dlp cache its JSON
        "download_archive": str(CACHE_DIR / "archive.txt"),  # ever processed
    }

    videos: List[Dict] = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name, meta in channels.items():
            url   = meta["url"].rstrip("/") + "/videos"
            topic = meta["topic"]
            print(f"Fetching: [{topic}] {name:<20} ({url})")

            try:
                playlist = ydl.extract_info(url, download=False)
                entries  = playlist.get("entries", [])[:max_videos]
            except Exception as e:
                print(f"  Error: {e}")
                continue

            for idx, entry in enumerate(entries, 1):
                vid   = entry["id"]
                tag   = f"{name[:2]}-{idx}/{len(entries)}"
                cfile = _cache_path(vid)

                if cfile.exists():
                    txt = cfile.read_text(encoding="utf-8")
                    print(f"  ✓ {tag} hit   ({len(txt)/1024:6.1f} kB, cache)")
                else:
                    print(f"  ▸ {tag} transcript …", end="", flush=True)
                    t0 = time.time()
                    try:
                        info = ydl.extract_info(entry["url"], download=False)
                        txt  = _get_transcript(vid, info)
                        cfile.write_text(txt, encoding="utf-8")
                        ok   = "✓"
                    except Exception:
                        txt, ok = entry.get("description", ""), "!"
                    dt = time.time() - t0
                    print(f"\r  {ok} {tag} done ({len(txt)/1024:6.1f} kB, {dt:4.1f}s)")

                videos.append(
                    dict(channel=name,
                         topic=topic,
                         title=entry.get("title", "Untitled"),
                         url=f"https://www.youtube.com/watch?v={vid}",
                         transcript=txt)
                )

    return videos
