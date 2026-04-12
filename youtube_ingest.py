#!/usr/bin/env python3
"""
YouTube Ingestion Pipeline
Extracts metadata, transcripts, and concepts from YouTube videos
and creates structured wiki entries in youtube_sources/.

Fallback chain (cloud-safe):
  Metadata  : yt-dlp → Invidious API → oEmbed (title only)
  Transcript: youtube-transcript-api → Invidious captions API
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # flagged at runtime only if Invidious path is needed

# ── Constants ────────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).parent
SOURCES_DIR = WORKSPACE / "youtube_sources"
TRANSCRIPTS_DIR = WORKSPACE / "transcripts"
TEMP_DIR = WORKSPACE / "youtube_ingest_temp"
TRANSCRIPT_SIZE_LIMIT = 50_000  # bytes

# Invidious public instances tried in order (see https://api.invidious.io)
INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://iv.datura.network",
    "https://invidious.nerdvpn.de",
    "https://invidious.privacyredirect.com",
]

# Topics that are in scope
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "neural network", "llm", "gpt", "transformer", "diffusion", "alignment",
    "agi", "model", "benchmark", "fine-tuning", "inference", "dataset",
    "reinforcement learning", "nlp", "computer vision", "robotics", "openai",
    "anthropic", "google deepmind", "mistral", "hugging face", "pytorch",
    "tensorflow", "cuda", "gpu", "training", "rlhf", "agent", "automation",
    "generative", "multimodal", "embedding", "vector", "retrieval",
    "mcp", "model context protocol", "trading", "claude",
]


# ── URL helpers ───────────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str | None:
    """Return the YouTube video ID from any standard URL format."""
    patterns = [
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/watch\?.*v=([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


# ── Tool checks ───────────────────────────────────────────────────────────────

def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def check_tools() -> dict:
    """Return availability of optional tools (non-fatal)."""
    ytdlp = _check_tool("yt-dlp")
    transcript_cli = (
        _check_tool("youtube-transcript") or _check_tool("youtube_transcript")
    )
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401
        transcript_api = True
    except ImportError:
        transcript_api = False

    return {
        "yt-dlp": ytdlp,
        "youtube-transcript-cli": transcript_cli,
        "youtube-transcript-api": transcript_api,
        "requests": requests is not None,
    }


# ── Invidious helpers ─────────────────────────────────────────────────────────

def _invidious_get(path: str, instance: str | None, timeout: int = 15) -> dict | list:
    """
    Try `instance` first; if None or failing, walk INVIDIOUS_INSTANCES.
    Returns parsed JSON or raises RuntimeError.
    """
    if requests is None:
        raise RuntimeError("requests not installed — pip install requests")

    candidates = ([instance] if instance else []) + [
        i for i in INVIDIOUS_INSTANCES if i != instance
    ]
    last_err = None
    for base in candidates:
        try:
            r = requests.get(f"{base}{path}", timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last_err = f"HTTP {r.status_code} from {base}"
        except Exception as e:
            last_err = str(e)
    raise RuntimeError(f"All Invidious instances failed. Last error: {last_err}")


# ── Step 2: Metadata ──────────────────────────────────────────────────────────

def _fetch_metadata_ytdlp(url: str, cookies: str | None, proxy: str | None) -> dict:
    cmd = ["yt-dlp", "--no-check-certificates", "--dump-json", "--no-download"]
    if cookies:
        cmd += ["--cookies", cookies]
    if proxy:
        cmd += ["--proxy", proxy]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def _fetch_metadata_invidious(video_id: str, instance: str | None) -> dict:
    data = _invidious_get(f"/api/v1/videos/{video_id}", instance)
    # Normalise to yt-dlp-like shape so summarise_metadata works unchanged
    published = data.get("published", 0)  # Unix timestamp
    if published:
        from datetime import timezone
        dt = datetime.fromtimestamp(published, tz=timezone.utc)
        upload_date = dt.strftime("%Y%m%d")
    else:
        upload_date = ""
    return {
        "title": data.get("title", "Unknown"),
        "channel": data.get("author", "Unknown"),
        "uploader": data.get("author", "Unknown"),
        "id": video_id,
        "upload_date": upload_date,
        "duration": data.get("lengthSeconds", 0),
        "description": (data.get("description") or "")[:500],
        "tags": data.get("keywords") or [],
        "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
    }


def _fetch_metadata_oembed(video_id: str) -> dict:
    """Last-resort: oEmbed gives title + channel only, no duration/date."""
    if requests is None:
        raise RuntimeError("requests not installed")
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"oEmbed HTTP {r.status_code}")
    d = r.json()
    return {
        "title": d.get("title", "Unknown"),
        "channel": d.get("author_name", "Unknown"),
        "uploader": d.get("author_name", "Unknown"),
        "id": video_id,
        "upload_date": "",
        "duration": 0,
        "description": "",
        "tags": [],
        "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
    }


def fetch_metadata(
    url: str,
    video_id: str,
    cookies: str | None = None,
    proxy: str | None = None,
    invidious_instance: str | None = None,
) -> dict:
    """
    Metadata with three-level fallback:
      1. yt-dlp (optionally with cookies/proxy)
      2. Invidious REST API
      3. YouTube oEmbed (title + channel only)
    """
    if _check_tool("yt-dlp"):
        try:
            return _fetch_metadata_ytdlp(url, cookies, proxy)
        except Exception as e:
            print(f"  [WARN] yt-dlp failed ({e}), trying Invidious...")

    try:
        return _fetch_metadata_invidious(video_id, invidious_instance)
    except Exception as e:
        print(f"  [WARN] Invidious metadata failed ({e}), trying oEmbed...")

    return _fetch_metadata_oembed(video_id)


def summarise_metadata(meta: dict) -> dict:
    """Extract the fields we care about from raw metadata dict."""
    duration_s = meta.get("duration", 0) or 0
    upload_raw = meta.get("upload_date", "")  # YYYYMMDD
    upload_date = (
        f"{upload_raw[:4]}-{upload_raw[4:6]}-{upload_raw[6:]}"
        if len(upload_raw) == 8 else upload_raw
    )
    return {
        "title": meta.get("title", "Unknown"),
        "channel": meta.get("channel") or meta.get("uploader", "Unknown"),
        "youtube_id": meta.get("id", ""),
        "upload_date": upload_date,
        "duration_s": duration_s,
        "duration": f"{duration_s // 60}m" if duration_s else "unknown",
        "description": (meta.get("description") or "")[:500],
        "tags": meta.get("tags") or [],
        "url": meta.get("webpage_url", ""),
    }


# ── Relevance gate ────────────────────────────────────────────────────────────

def is_ai_relevant(info: dict) -> tuple[bool, str]:
    """Return (relevant, reason) based on title/tags/description."""
    text = " ".join([
        info.get("title", ""),
        info.get("channel", ""),
        info.get("description", ""),
        " ".join(info.get("tags", [])),
    ]).lower()

    matched = [kw for kw in AI_KEYWORDS if kw in text]
    if matched:
        return True, f"Matched keywords: {', '.join(matched[:5])}"
    return False, "No AI/ML keywords found in title, description, or tags"


# ── Step 3: Transcript ────────────────────────────────────────────────────────

def _fetch_transcript_api(
    video_id: str,
    proxy: str | None = None,
) -> str:
    """Fetch via youtube-transcript-api Python library."""
    from youtube_transcript_api import YouTubeTranscriptApi

    kwargs = {}
    if proxy:
        kwargs["proxies"] = {"https": proxy, "http": proxy}

    api = YouTubeTranscriptApi(**kwargs)
    snippets = list(api.fetch(video_id))
    lines = []
    for s in snippets:
        # v1.x returns FetchedTranscriptSnippet objects with .text and .start
        start = getattr(s, "start", None) or s.get("start", 0)
        text = getattr(s, "text", None) or s.get("text", "")
        mm = int(start) // 60
        ss = int(start) % 60
        lines.append(f"[{mm:02d}:{ss:02d}] {text}")
    return "\n".join(lines)


def _fetch_transcript_invidious(video_id: str, instance: str | None) -> str:
    """
    Fetch captions list from Invidious, then download the first
    available auto-generated or manual caption track as plain text.
    """
    data = _invidious_get(f"/api/v1/captions/{video_id}", instance)
    captions = data.get("captions", [])
    if not captions:
        raise RuntimeError("No captions listed by Invidious")

    # Prefer English; fall back to first available
    track = next(
        (c for c in captions if c.get("language_code", "").startswith("en")),
        captions[0],
    )
    label = track.get("label", "")
    lang_code = track.get("language_code", "en")

    # Determine which Invidious instance actually responded
    candidates = ([instance] if instance else []) + [
        i for i in INVIDIOUS_INSTANCES if i != instance
    ]
    vtt_url = None
    for base in candidates:
        try:
            r = requests.get(
                f"{base}/api/v1/captions/{video_id}",
                params={"label": label, "lang": lang_code},
                timeout=10,
            )
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("text"):
                return _vtt_to_plain(r.text)
            # Some instances return JSON with a URL instead
            try:
                payload = r.json()
                vtt_url = payload.get("url")
                if vtt_url:
                    break
            except Exception:
                pass
        except Exception:
            continue

    if vtt_url:
        r = requests.get(vtt_url, timeout=20)
        if r.status_code == 200:
            return _vtt_to_plain(r.text)

    raise RuntimeError("Could not download caption track from Invidious")


def _vtt_to_plain(vtt: str) -> str:
    """Convert WebVTT / SRT text to plain timestamped lines."""
    lines = []
    ts_re = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.\d+\s*-->")
    current_ts = ""
    for raw in vtt.splitlines():
        raw = raw.strip()
        m = ts_re.match(raw)
        if m:
            h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
            total_s = h * 3600 + mi * 60 + s
            mm = total_s // 60
            ss = total_s % 60
            current_ts = f"[{mm:02d}:{ss:02d}]"
        elif raw and not raw.startswith("WEBVTT") and not raw.isdigit() and "-->" not in raw:
            # Strip HTML tags sometimes present in VTT
            clean = re.sub(r"<[^>]+>", "", raw)
            if clean and current_ts:
                lines.append(f"{current_ts} {clean}")
                current_ts = ""
    return "\n".join(lines)


def fetch_transcript(
    url: str,
    video_id: str,
    cookies: str | None = None,
    proxy: str | None = None,
    invidious_instance: str | None = None,
) -> tuple[str, str]:
    """
    Fetch transcript with two-level fallback:
      1. youtube-transcript-api (optionally with proxy)
      2. Invidious captions API

    Returns (transcript_text, storage_path).
    storage_path is '' when inlined (<50KB), or path when saved.
    """
    transcript = ""

    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401
        transcript = _fetch_transcript_api(video_id, proxy)
        print("  Source: youtube-transcript-api")
    except Exception as e:
        print(f"  [WARN] youtube-transcript-api failed ({e}), trying Invidious...")
        try:
            transcript = _fetch_transcript_invidious(video_id, invidious_instance)
            print("  Source: Invidious captions API")
        except Exception as e2:
            print(f"  [WARN] Invidious captions failed ({e2}) — no transcript available")
            return "", ""

    if not transcript:
        return "", ""

    size = len(transcript.encode("utf-8"))
    if size >= TRANSCRIPT_SIZE_LIMIT:
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = TRANSCRIPTS_DIR / f"{video_id}_transcript.txt"
        out_path.write_text(transcript, encoding="utf-8")
        preview = transcript[:300] + "\n\n[... truncated — see full file ...]"
        return preview, str(out_path)

    return transcript, ""


# ── Step 4: Concept extraction ────────────────────────────────────────────────

def extract_concepts(transcript: str, info: dict) -> dict:
    """
    Lightweight heuristic extraction of concepts from the transcript.
    A real deployment would call an LLM here; this gives a
    structured skeleton that agents / humans can fill in.
    """
    known_models = [
        "gpt-4", "gpt-3", "claude", "gemini", "llama", "mistral",
        "falcon", "stable diffusion", "dall-e", "whisper", "bert",
        "t5", "palm", "bard", "copilot", "codex",
    ]
    text = transcript.lower()
    mentioned_models = [m for m in known_models if m in text]

    ts_pattern = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]")
    timestamps = ts_pattern.findall(transcript)

    concepts = list({kw for kw in AI_KEYWORDS if kw in text})[:10]

    return {
        "mentioned_models": mentioned_models,
        "timestamps_found": timestamps[:10],
        "concepts": concepts,
    }


# ── Step 5: Wiki file ─────────────────────────────────────────────────────────

def _slugify(text: str, max_len: int = 40) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:max_len]


def create_wiki_entry(info: dict, transcript: str, transcript_path: str, concepts: dict) -> Path:
    """Write the wiki markdown file and return its path."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    channel_slug = _slugify(info["channel"])
    title_slug = _slugify(info["title"])
    vid = info["youtube_id"]
    filename = f"video_{channel_slug}_{title_slug}_{vid}.md"
    out_path = SOURCES_DIR / filename

    if concepts["timestamps_found"]:
        claims_yaml = "\n".join(
            f'  - "Key point at [{ts}] — fill in during review"'
            for ts in concepts["timestamps_found"][:5]
        )
    else:
        claims_yaml = '  - "No timestamps detected — review transcript manually"'

    topic_list = ", ".join(concepts["concepts"][:5]) or "AI"
    model_list = ", ".join(concepts["mentioned_models"]) or "none detected"

    transcript_section = (
        f"**Transcript stored at:** `{transcript_path}`\n\n"
        f"*(File exceeds 50 KB — inline display suppressed)*\n\n"
        f"Preview:\n```\n{transcript[:400]}\n```"
        if transcript_path
        else (
            f"```\n{transcript}\n```"
            if transcript
            else "*No transcript available for this video.*"
        )
    )

    ingested_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    content = textwrap.dedent(f"""\
        ---
        title: "{info['title'].replace('"', "'")}"
        channel: "{info['channel'].replace('"', "'")}"
        youtube_id: "{vid}"
        upload_date: "{info['upload_date']}"
        duration: "{info['duration']}"
        url: "{info['url']}"
        topic: [{topic_list}]
        concepts: [{", ".join(concepts['concepts'][:8])}]
        models_mentioned: [{model_list}]
        key_claims:
        {claims_yaml}
        transcript_path: "{transcript_path or 'inline'}"
        ingested_at: "{ingested_at}"
        status: ingested
        ---

        # {info['title']}

        **Channel:** {info['channel']}
        **Duration:** {info['duration']}
        **Uploaded:** {info['upload_date']}
        **URL:** {info['url']}

        ---

        ## Summary

        > *Auto-generated skeleton. Expand with LLM-assisted analysis or manual review.*

        {info['description'] or '_No description available._'}

        ---

        ## Key Insights

        *(Fill in timestamped insights after reviewing the transcript)*

        {chr(10).join(f'- [{ts}] — ' for ts in concepts['timestamps_found'][:5]) or '- No timestamps detected.'}

        ---

        ## Technical Details

        **Models / Tools Mentioned:** {model_list}

        *(Add benchmark results, architecture details, code repositories here)*

        ---

        ## Follow-up Resources

        - [ ] Check linked papers in description
        - [ ] Search for related talks by same channel
        - [ ] Cross-reference with existing wiki entries

        ---

        ## Transcript

        {transcript_section}
        """)

    out_path.write_text(content, encoding="utf-8")
    return out_path


# ── Cleanup ───────────────────────────────────────────────────────────────────

def cleanup_temp():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


# ── Main orchestration ────────────────────────────────────────────────────────

def ingest(
    url: str,
    force: bool = False,
    skip_relevance: bool = False,
    cookies: str | None = None,
    proxy: str | None = None,
    invidious_instance: str | None = None,
) -> int:
    """Full 5-step ingestion. Returns 0 on success, 1 on skip/error."""
    print(f"\n{'─'*60}")
    print(f"  YouTube Ingestion Pipeline")
    print(f"{'─'*60}")
    print(f"  URL: {url}")

    tools = check_tools()
    active = [k for k, v in tools.items() if v]
    print(f"  Tools available: {', '.join(active) or 'none'}")
    if not tools["requests"]:
        print("  [WARN] requests not installed — Invidious fallback unavailable")
        print("         Install with: pip install requests")

    # STEP 1 — Validate URL
    print("\n[STEP 1] Validating URL...")
    video_id = extract_video_id(url)
    if not video_id:
        print(f"[ERROR] Could not extract video ID from: {url}")
        return 1
    print(f"  Video ID: {video_id}")

    # STEP 2 — Metadata
    print("\n[STEP 2] Fetching metadata...")
    try:
        raw_meta = fetch_metadata(url, video_id, cookies, proxy, invidious_instance)
        info = summarise_metadata(raw_meta)
    except Exception as e:
        print(f"[ERROR] All metadata sources failed: {e}")
        return 1

    print(f"  Title   : {info['title']}")
    print(f"  Channel : {info['channel']}")
    print(f"  Duration: {info['duration']}")
    print(f"  Date    : {info['upload_date']}")

    # Relevance gate
    if not skip_relevance:
        relevant, reason = is_ai_relevant(info)
        if not relevant and not force:
            print(f"\n[SKIP] Not AI-relevant: {reason}")
            return 1
        if not relevant:
            print(f"\n[WARN] Relevance check failed ({reason}), proceeding due to --force")
        else:
            print(f"  Relevant: YES ({reason})")

    # STEP 3 — Transcript
    print("\n[STEP 3] Extracting transcript...")
    try:
        transcript, transcript_path = fetch_transcript(
            url, video_id, cookies, proxy, invidious_instance
        )
        if not transcript:
            print("  [WARN] No transcript available — metadata-only entry will be created.")
        elif transcript_path:
            size_kb = os.path.getsize(transcript_path) / 1024
            print(f"  Saved to: {transcript_path} ({size_kb:.1f} KB)")
        else:
            print(f"  Transcript size: {len(transcript.encode())} bytes (inlined)")
    except Exception as e:
        print(f"  [WARN] Transcript extraction error: {e}")
        transcript, transcript_path = "", ""

    # STEP 4 — Concepts
    print("\n[STEP 4] Extracting concepts...")
    concepts = extract_concepts(transcript, info)
    print(f"  Concepts     : {', '.join(concepts['concepts'][:5]) or 'none'}")
    print(f"  Models found : {', '.join(concepts['mentioned_models']) or 'none'}")
    print(f"  Timestamps   : {len(concepts['timestamps_found'])} detected")

    # STEP 5 — Wiki file
    print("\n[STEP 5] Creating wiki entry...")
    wiki_path = create_wiki_entry(info, transcript, transcript_path, concepts)
    print(f"  Wiki file: {wiki_path}")

    cleanup_temp()
    print(f"\n[DONE] Ingestion complete.")
    print(f"{'─'*60}\n")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="YouTube Ingestion Pipeline — extract metadata, transcript, and concepts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Fallback chain
            ──────────────
            Metadata  : yt-dlp → Invidious API → oEmbed
            Transcript: youtube-transcript-api → Invidious captions

            Examples
            ────────
            # Standard run (auto-selects best available source)
            python youtube_ingest.py "https://youtu.be/vIX6ztULs4U"

            # With browser cookies (bypasses YouTube bot-check on local runs)
            python youtube_ingest.py "URL" --cookies ~/cookies.txt

            # Force a specific Invidious instance
            python youtube_ingest.py "URL" --invidious-instance https://inv.nadeko.net

            # Residential proxy (for long-running cloud deployments)
            python youtube_ingest.py "URL" --proxy http://user:pass@proxy:port

            # Batch ingest, skip relevance filter
            python youtube_ingest.py "URL1" "URL2" --skip-relevance-check
        """),
    )
    parser.add_argument("urls", nargs="+", help="One or more YouTube URLs to ingest")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Ingest even if relevance gate fails")
    parser.add_argument("--skip-relevance-check", action="store_true",
                        help="Bypass the AI/ML topic relevance filter entirely")
    parser.add_argument("--cookies", metavar="PATH",
                        help="Path to cookies.txt (Netscape format) for yt-dlp")
    parser.add_argument("--proxy", metavar="URL",
                        help="HTTP/HTTPS proxy for yt-dlp and youtube-transcript-api")
    parser.add_argument("--invidious-instance", metavar="URL",
                        help="Preferred Invidious instance base URL (e.g. https://inv.nadeko.net)")
    parser.add_argument("--check-tools", action="store_true",
                        help="Report tool availability and exit")

    args = parser.parse_args()

    if args.check_tools:
        tools = check_tools()
        for name, available in tools.items():
            status = "OK" if available else "MISSING"
            print(f"  {status:7s}  {name}")
        if not tools["yt-dlp"] and not tools["requests"]:
            print("\nAt minimum, install requests for Invidious fallback:")
            print("  pip install requests")
        sys.exit(0)

    exit_codes = []
    for url in args.urls:
        code = ingest(
            url,
            force=args.force,
            skip_relevance=args.skip_relevance_check,
            cookies=args.cookies,
            proxy=args.proxy,
            invidious_instance=args.invidious_instance,
        )
        exit_codes.append(code)

    sys.exit(1 if any(c != 0 for c in exit_codes) else 0)


if __name__ == "__main__":
    main()
