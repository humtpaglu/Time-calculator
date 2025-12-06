# Time-calculator
```markdown
Time-summing Telegram Bot (video files)

What this bot does
- Accepts video files sent as native Telegram videos (video messages), animations, or as documents (e.g., .mp4, .mkv, .mov).
- Detects the duration of each received video.
  - For native Telegram Video/Animation messages it uses the metadata Telegram provides.
  - For video files sent as documents it downloads the file and probes duration using ffprobe (part of FFmpeg).
- Keeps a running total of durations per chat (in memory).
- Commands:
  - /start — info and quick usage
  - /total — show current summed duration for this chat
  - /reset — reset the running sum for this chat
  - Send a video or send a video file as a document — the bot will add the duration and reply with the new total.

Requirements
- Python 3.10+
- ffmpeg (for document video duration probing). Install ffmpeg on your system:
  - Debian/Ubuntu: sudo apt install ffmpeg
  - macOS (Homebrew): brew install ffmpeg
  - Windows: download from https://ffmpeg.org and add to PATH
- Python packages:
  - python-telegram-bot

Quick start
1. Install Python dependencies:
   pip install -r requirements.txt

2. Install ffmpeg on the server/machine running the bot.

3. Set the bot token:
   export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."  (or set env var appropriately on Windows)

4. Run:
   python bot.py

Notes & limitations
- Running totals are stored in memory (per chat). They reset if the process restarts. If you need persistence, I can add a simple SQLite or file-backed store.
- ffprobe (part of ffmpeg) must be available in PATH for probing arbitrary video files sent as documents. For native Telegram Video messages, ffmpeg is not required.
- This bot sums durations per chat. If you want per-user totals, group-wide totals, or per-session behavior, tell me and I’ll adjust.

Extending ideas
- Persist totals in SQLite or Redis.
- Add a command to export totals as CSV or JSON.
- Support batch uploads (e.g., zip of videos) by extracting and probing each file.
- Add a /mode to switch aggregation scope (per-user, per-chat, global).

```
