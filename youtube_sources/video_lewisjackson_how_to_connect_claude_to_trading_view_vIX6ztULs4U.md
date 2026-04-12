---
title: "How To Connect Claude to Trading View (Insanely Cool)"
channel: "Lewis Jackson"
channel_url: "https://www.youtube.com/@LewisWJackson"
youtube_id: "vIX6ztULs4U"
upload_date: "2026-04"
duration: "~10-15m"
url: "https://youtu.be/vIX6ztULs4U"
topic: [AI, MCP, Trading, Claude, TradingView, Automation]
concepts: [MCP, Chrome DevTools Protocol, Pine Script, Claude Code, TradingView Desktop, webhook, automated trading, morning brief, session bias, watchlist scanning]
models_mentioned: [claude]
tools_mentioned: [Claude Code, TradingView Desktop, Node.js, ngrok, Railway, BitGet, Apify]
repos:
  - "https://github.com/LewisWJackson/tradingview-mcp-jackson"
  - "https://github.com/jackson-video-resources/claude-tradingview-mcp-trading"
key_claims:
  - "Claude reads TradingView's underlying code values via CDP — not screenshots"
  - "81 MCP tools exposed: chart control, indicator reads, Pine Script dev, drawings, alerts"
  - "Morning Brief workflow scans full watchlist and generates session bias automatically"
  - "One-shot setup prompt: copy, paste into Claude Code, answer 3 yes/no questions — done"
  - "This is the prerequisite first video — second video adds automated trade execution on BitGet"
transcript_path: "inline"
ingested_at: "2026-04-12T00:00:00Z"
status: ingested
ingestion_note: "Transcript unavailable due to IP block (cloud environment). Entry synthesised from oEmbed metadata, associated GitHub READMEs, and secondary sources."
---

# How To Connect Claude to Trading View (Insanely Cool)

**Channel:** Lewis Jackson ([@LewisWJackson](https://www.youtube.com/@LewisWJackson))
**Duration:** ~10-15 min (estimated)
**Uploaded:** April 2026
**URL:** https://youtu.be/vIX6ztULs4U

---

## Summary

Lewis Jackson demonstrates how to connect **Claude Code** directly to **TradingView Desktop** using a custom MCP (Model Context Protocol) server built on the Chrome DevTools Protocol. Unlike screenshot-based AI trading tools, this integration reads TradingView's live chart data at the code level — indicator values, OHLCV data, Pine Script state — making Claude a first-class citizen inside the charting environment.

The setup is deliberately low-friction: clone a repo, run `npm install`, launch TradingView with a debug flag, add a single line to `~/.claude/.mcp.json`, and verify with a health check. A "one-shot setup prompt" is provided that lets Claude Code handle the entire configuration interactively.

This video is explicitly framed as **Part 1** of a series. Part 2 (github.com/jackson-video-resources/claude-tradingview-mcp-trading) extends the setup to execute live trades on crypto exchanges (BitGet, Binance, Bybit, and others) with Railway-hosted cron scheduling and CSV tax accounting.

---

## Key Insights

### Architecture — How It Actually Works

Claude does not analyse chart screenshots. The MCP server connects to TradingView Desktop via **Chrome DevTools Protocol (CDP) on `localhost:9222`** — the same debugging interface used by browser DevTools. TradingView Desktop is a Chromium-based app, so CDP works natively once the debug port is enabled via a launch flag.

All processing is **local only** — no data leaves the machine, no external API calls beyond Claude itself.

### The 81 MCP Tools

The `tradingview-mcp-jackson` server exposes 81 tools to Claude Code:

| Category | Examples |
|----------|---------|
| Chart control | Switch symbol/timeframe, chart type, multi-pane layouts (2×2, 3×1) |
| Data reads | OHLCV candles, indicator values, custom Pine Script drawings |
| Indicator management | Add/remove indicators, adjust settings |
| Pine Script dev | Write, compile, inject, debug, save to TradingView cloud |
| Drawing tools | Trend lines, horizontal levels, text annotations |
| Price alerts | Create and manage alerts |
| Navigation | Go-to-date, replay mode for backtesting |
| Screenshots | Capture chart as image |
| Morning Brief (new) | Watchlist scan, rules application, session bias summary |

### Morning Brief Workflow

The headline feature in this fork. Claude cycles through a user-defined watchlist, reads all indicator values per asset, applies trading rules from a `rules.json` file (written in plain English), and returns a structured **session bias** — bullish / bearish / neutral — per symbol. This turns a 45-minute morning routine into a single command.

### Pine Script on Demand

Natural-language Pine Script generation is a first-class use case. Claude writes TradingView's native scripting language from a description, injects it live, watches for compile errors, iterates, and saves to the cloud. Strategies from classic setups (RSI + MACD, van de Poppe + Tone Vays methodology) to fully custom indicators are supported.

### Natural Language Chart Control

Direct commands like *"show me Bitcoin on the weekly"* or *"remove the volume indicator"* execute without menu navigation. The friction of the TradingView UI collapses entirely.

---

## Technical Details

### Prerequisites

- **TradingView Desktop** (paid subscription required; free tier does not expose CDP)
- **Node.js 18+**
- **Claude Code** installed and authenticated
- macOS, Windows, or Linux

### Installation (MCP Server)

```bash
git clone https://github.com/LewisWJackson/tradingview-mcp-jackson.git ~/tradingview-mcp-jackson
cd ~/tradingview-mcp-jackson
npm install
cp rules.example.json rules.json   # configure your trading rules
```

### Launch TradingView with Debug Port

The repo ships helper scripts (`tv_launch`) that start TradingView with `--remote-debugging-port=9222`. This is a standard Chromium flag — no patching or reverse engineering of TradingView's protocol.

### MCP Configuration

Add to `~/.claude/.mcp.json`:

```json
{
  "tradingview": {
    "command": "node",
    "args": ["/path/to/tradingview-mcp-jackson/index.js"]
  }
}
```

### Health Check

```bash
tv_health_check
# Expected: cdp_connected: true
```

### `rules.json` Structure

Plain-English trading rules stored in a JSON file. Defines entry conditions, exit signals, risk tolerance, and timeframes. Claude reads this file when running the Morning Brief or generating strategies.

---

## Part 2: Automated Trade Execution

The follow-up repository (`jackson-video-resources/claude-tradingview-mcp-trading`) adds:

- **Exchange integration**: BitGet featured; also Binance, Bybit, OKX, Coinbase Advanced, Kraken, KuCoin, Gate.io, MEXC, Bitfinex
- **Execution flow**: fetch live data → calculate MACD → determine bias → safety check → execute trade
- **Safety rails**: max position size, daily trade limit, 1% portfolio risk cap, full audit log
- **Cloud deployment**: Railway + cron scheduling (e.g. `0 */4 * * *` for 4H charts)
- **Tax accounting**: CSV output per trade with ISO date, symbol, price, fees, order ID
- **Paper trading mode**: default `PAPER_TRADING=true` — observe decisions before going live

**One-shot deployment prompt** (`prompts/02-one-shot-trade.md`): paste into Claude Code, answer a few yes/no questions, and Claude handles cloning, credential setup, TradingView connection, strategy selection, Railway deploy, and initial test run.

---

## Follow-up Resources

- [tradingview-mcp-jackson repo](https://github.com/LewisWJackson/tradingview-mcp-jackson) — MCP server (81 tools)
- [claude-tradingview-mcp-trading repo](https://github.com/jackson-video-resources/claude-tradingview-mcp-trading) — automated trading bot (Part 2)
- [Lazy Tech Talk guide](https://www.lazytechtalk.com/guides/connect-claude-code-to-tradingview-with-mcp-a-developers-guide) — written walkthrough
- [Medium: Claude Just Took Over TradingView](https://medium.com/@crypto-deploy/claude-just-took-over-tradingview-here-is-what-that-actually-means-130bc0daad77) — secondary analysis
- [Apify YouTube Transcript Scraper](https://apify.com) — used in Part 2 for scraping trader strategy content

---

## Transcript

*Transcript could not be retrieved automatically — the ingestion environment (cloud IP) is blocked by YouTube's rate-limiting. Entry was synthesised from:*

- *YouTube oEmbed metadata*
- *GitHub README of `tradingview-mcp-jackson` (primary source for video content)*
- *GitHub README of `claude-tradingview-mcp-trading` (explicitly references this video as prerequisite)*
- *[Lazy Tech Talk written guide](https://www.lazytechtalk.com/guides/connect-claude-code-to-tradingview-with-mcp-a-developers-guide)*
- *[Medium article](https://medium.com/@crypto-deploy/claude-just-took-over-tradingview-here-is-what-that-actually-means-130bc0daad77)*

*To get the actual transcript when running locally:*

```bash
youtube-transcript "https://youtu.be/vIX6ztULs4U" --digest > transcripts/vIX6ztULs4U_transcript.txt
```
