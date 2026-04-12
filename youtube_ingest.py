#!/usr/bin/env python3
"""
YouTube Ingestion Pipeline
Extracts metadata, transcripts, and concepts from YouTube videos
and creates structured wiki entries in youtube_sources/.
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

# ── Constants ────────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).parent
SOURCES_DIR = WORKSPACE / "youtube_sources"
TRANSCRIPTS_DIR = WORKSPACE / "transcripts"
TEMP_DIR = WORKSPACE / "youtube_ingest_temp"
TRANSCRIPT_SIZE_LIMIT = 50_000  # bytes

# Topics that are in scope
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "neural network", "llm", "gpt", "transformer", "diffusion", "alignment",
    "agi", "model", "benchmark", "fine-tuning", "inference", "dataset",
    "reinforcement learning", "nlp", "computer vision", "robotics", "openai",
    "anthropic", "google deepmind", "mistral", "hugging face", "pytorch",
    "tensorflow", "cuda", "gpu", "training", "rlhf", "agent", "automation",
    "generative", "multimodal", "embedding", "vector", "retrieval",
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


def ensure_tools() -> list[str]:
    """Return list of missing tool names."""
    missing = []
    if not _check_tool("yt-dlp"):
        missing.append("yt-dlp")
    # youtube-transcript installs as 'youtube-transcript' or 'youtube_transcript'
    if not (_check_tool("youtube-transcript") or _check_tool("youtube_transcript")):
        missing.append("youtube-transcript")
    return missing


# ── Step 2: Metadata ──────────────────────────────────────────────────────────

def fetch_metadata(url: str) -> dict:
    """Use yt-dlp to fetch video metadata as a dict."""
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", url],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def summarise_metadata(meta: dict) -> dict:
    """Extract the fields we care about from raw yt-dlp JSON."""
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
        "duration": f"{duration_s // 60}m",
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

def _transcript_cmd() -> str:
    """Return the available transcript CLI name."""
    for name in ("youtube-transcript", "youtube_transcript"):
        if _check_tool(name):
            return name
    raise RuntimeError("youtube-transcript not found. Install: pip install youtube-transcript")


def fetch_transcript(url: str, video_id: str) -> tuple[str, str]:
    """
    Fetch transcript in digest mode.
    Returns (transcript_text, storage_path).
    storage_path is '' when transcript is inlined (<5KB),
    or the path where it was saved (>=5KB).
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    digest_path = TEMP_DIR / f"{video_id}_digest.txt"
    cmd = _transcript_cmd()

    result = subprocess.run(
        [cmd, url, "--digest"],
        capture_output=True, text=True, timeout=120,
    )

    # Some versions print a size warning to stderr when digest is needed
    if "MUST use --digest" in (result.stderr or ""):
        raise RuntimeError("Transcript too large even for digest mode — manual review required.")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "No transcript" in stderr or "no captions" in stderr.lower():
            return "", ""
        raise RuntimeError(f"youtube-transcript failed: {stderr}")

    transcript = result.stdout.strip()
    size = len(transcript.encode("utf-8"))

    if size >= TRANSCRIPT_SIZE_LIMIT:
        # Save to transcripts/ and return reference path
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = TRANSCRIPTS_DIR / f"{video_id}_transcript.txt"
        out_path.write_text(transcript, encoding="utf-8")
        return transcript[:200] + "\n\n[... truncated — see full file ...]", str(out_path)

    return transcript, ""


# ── Step 4: Concept extraction ────────────────────────────────────────────────

def extract_concepts(transcript: str, info: dict) -> dict:
    """
    Lightweight heuristic extraction of concepts from the transcript.
    A real deployment would call an LLM here; this gives a
    structured skeleton that agents / humans can fill in.
    """
    # Collect model/tool names that appear in the transcript
    known_models = [
        "gpt-4", "gpt-3", "claude", "gemini", "llama", "mistral",
        "falcon", "stable diffusion", "dall-e", "whisper", "bert",
        "t5", "palm", "bard", "copilot", "codex",
    ]
    mentioned_models = [m for m in known_models if m in transcript.lower()]

    # Simple timestamp pattern: [HH:MM:SS] or [MM:SS]
    ts_pattern = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]")
    timestamps = ts_pattern.findall(transcript)

    # Concepts from tags + simple keyword scan
    concepts = list({
        kw for kw in AI_KEYWORDS if kw in transcript.lower()
    })[:10]

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

    # Build key_claims placeholder list
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
        f"*(File exceeds 5 KB — inline display suppressed)*\n\n"
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

def ingest(url: str, force: bool = False, skip_relevance: bool = False) -> int:
    """
    Full 5-step ingestion. Returns exit code (0 = success, 1 = skipped/error).
    """
    print(f"\n{'─'*60}")
    print(f"  YouTube Ingestion Pipeline")
    print(f"{'─'*60}")
    print(f"  URL: {url}")

    # Check tools
    missing = ensure_tools()
    if missing:
        print(f"\n[ERROR] Missing required tools: {', '.join(missing)}")
        print("Install with:")
        for t in missing:
            print(f"  pip install {t}")
        return 1

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
        raw_meta = fetch_metadata(url)
        info = summarise_metadata(raw_meta)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
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
        transcript, transcript_path = fetch_transcript(url, video_id)
        if not transcript:
            print("  [WARN] No transcript available — metadata-only entry will be created.")
        elif transcript_path:
            size_kb = os.path.getsize(transcript_path) / 1024
            print(f"  Transcript saved to: {transcript_path} ({size_kb:.1f} KB)")
        else:
            size_bytes = len(transcript.encode())
            print(f"  Transcript size: {size_bytes} bytes (inlined)")
    except RuntimeError as e:
        print(f"  [WARN] Transcript extraction failed: {e}")
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

    # Cleanup
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
            Examples:
              python youtube_ingest.py "https://youtu.be/dQw4w9WgXcQ"
              python youtube_ingest.py "https://www.youtube.com/watch?v=abc123" --force
              python youtube_ingest.py "URL1" "URL2" "URL3" --skip-relevance-check
        """),
    )
    parser.add_argument("urls", nargs="+", help="One or more YouTube URLs to ingest")
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Ingest even if relevance gate fails",
    )
    parser.add_argument(
        "--skip-relevance-check",
        action="store_true",
        help="Bypass the AI/ML topic relevance filter entirely",
    )
    parser.add_argument(
        "--check-tools",
        action="store_true",
        help="Check whether required tools are installed and exit",
    )

    args = parser.parse_args()

    if args.check_tools:
        missing = ensure_tools()
        if missing:
            print(f"Missing tools: {', '.join(missing)}")
            print("Install with: pip install " + " ".join(missing))
            sys.exit(1)
        else:
            print("All required tools are installed.")
            sys.exit(0)

    exit_codes = []
    for url in args.urls:
        code = ingest(url, force=args.force, skip_relevance=args.skip_relevance_check)
        exit_codes.append(code)

    # Exit 1 if any ingestion failed
    sys.exit(1 if any(c != 0 for c in exit_codes) else 0)


if __name__ == "__main__":
    main()
