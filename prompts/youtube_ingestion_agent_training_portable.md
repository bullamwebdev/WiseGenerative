# YouTube Video Ingestion Agent — Portable Training Guide

**Purpose:** Teach any agent to extract transcripts, metadata, and concepts from YouTube videos for knowledge storage.  
**Environment:** AGNOSTIC — works on any system with required tools installed.

---

## SCOPE & BOUNDARIES

### What to ingest:
- AI/ML research talks, model releases, alignment discussions
- Technical tutorials, conference presentations
- Interviews with AI researchers, engineers
- Policy discussions about AI governance

### What to SKIP (relevance gate):
- Health/longevity content (unless AI-related)
- Lifestyle/self-improvement
- Entertainment, gaming, vlogs
- Business/marketing without AI focus

---

## REQUIRED TOOLS (Install if missing)

### Tool 1: youtube-transcript
```bash
pip install youtube-transcript
```

**Usage — ALWAYS start with digest mode:**
```bash
youtube-transcript "<URL>" --digest > video_digest.txt
```

> **CRITICAL:** If you see `"NNNN est tokens — caller MUST use --digest"`, SWITCH immediately.  
> Never process >50KB transcripts inline.

### Tool 2: yt-dlp
```bash
pip install yt-dlp
```

**Usage — metadata only:**
```bash
yt-dlp --dump-json --no-download "<URL>" > metadata.json
```

---

## 5-STEP PORTABLE WORKFLOW

### STEP 1: Validate URL
Extract video ID from `youtu.be/ID` or `youtube.com/watch?v=ID`

### STEP 2: Extract Metadata
```bash
yt-dlp --dump-json --no-download "<URL>" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'Title: {d.get(\"title\")}')
print(f'Channel: {d.get(\"channel\")}')
print(f'Duration: {d.get(\"duration\",0)//60}m')
"
```

### STEP 3: Extract Transcript
```bash
mkdir -p youtube_ingest_temp
cd youtube_ingest_temp

# Digest mode (bounded ~5KB)
youtube-transcript "<URL>" --digest > transcript.txt

# Check size — CRITICAL
ls -lh transcript.txt
```

### STEP 4: Analyze Content

Extract from transcript:
- Core thesis (1-2 sentences)
- Key claims (3-5 with timestamps [MM:SS])
- Technical details (models, benchmarks)
- Speakers/repos/papers mentioned
- Contrarian views

### STEP 5: Create Wiki File

**Location:** `youtube_sources/` (create in your workspace)  
**Filename:** `video_{channel}_{title}_{id}.md`

**Frontmatter:**
```yaml
---
title: "Full Title"
channel: "Channel"
youtube_id: "ID"
upload_date: "YYYY-MM-DD"
duration: "Xm"
topic: [AI, ML]
concepts: [concept1, concept2]
key_claims:
  - "Claim [MM:SS]"
status: ingested
---
```

**Body Sections:**
- Summary (2-3 paragraphs)
- Key Insights (timestamped sections)
- Technical Details
- Follow-up Resources
- Transcript (inline if <5KB, else reference path)

---

## ERROR HANDLING

| Error             | Response                                |
|-------------------|-----------------------------------------|
| Tool not found    | Install via pip/apt/brew                |
| Video unavailable | Report, skip                            |
| No transcript     | Metadata only                           |
| Transcript >50KB  | Save to `transcripts/`, reference by path |
| Rate limited      | Wait 60s, retry once                    |
| Non-AI content    | Skip with reason                        |

---

## DIRECTORY STRUCTURE

```
your_workspace/
├── youtube_sources/      # Wiki entries
├── transcripts/          # Large raw files
└── youtube_ingest_temp/  # Working dir (cleanup after)
```

---

## COMPLETION CHECKLIST

- [ ] Tools installed
- [ ] Metadata extracted
- [ ] Transcript extracted
- [ ] File size checked (handle >50KB)
- [ ] Key concepts + timestamps captured
- [ ] Wiki file created with YAML frontmatter
- [ ] Large files referenced by path
- [ ] Temp directory cleaned up

---

## PRO TIPS

1. Always use `--digest` first — prevents memory overflow
2. Check file sizes — `ls -lh` before reading
3. Timestamp everything — makes content navigable
4. Reference by path — never inline >50KB
5. Clean up temp files

---

## QUICK REFERENCE

**Metadata one-liner:**
```bash
yt-dlp --dump-json --no-download "URL" | python3 -c "import json,sys;d=json.load(sys.stdin);print(f'{d[\"title\"]} ({d[\"duration\"]//60}m)')"
```

**Transcript one-liner:**
```bash
youtube-transcript "URL" --digest > digest.txt
```

**Size check:**
```bash
ls -lh digest.txt && [ $(wc -c < digest.txt) -lt 50000 ] && echo "OK" || echo "TOO LARGE"
```

---

**Success Criteria:** Wiki file exists with valid YAML, core concepts + timestamps, technical details, and transcript either inline (<5KB) or referenced by path (>5KB).

---

*Created: 2026-04-12 | Version: 1.0 (Portable)*
