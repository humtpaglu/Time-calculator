import os
import subprocess
import tempfile
from datetime import timedelta
from typing import Optional, Dict

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# In-memory totals per chat_id (seconds)
chat_totals: Dict[int, int] = {}

VIDEO_EXTENSIONS = {
    ".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".flv", ".wmv", ".mpeg", ".mpg", ".3gp", ".ogv"
}


def human_readable_seconds(seconds: int) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours}h {minutes}m {secs}s"


def get_duration_with_ffprobe(path: str) -> Optional[float]:
    """
    Use ffprobe to get the duration of a media file in seconds.
    Returns float seconds or None if ffprobe is not available or fails.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
    except FileNotFoundError:
        # ffprobe not installed / not in PATH
        return None
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    out = proc.stdout.strip()
    if not out:
        return None

    try:
        return float(out)
    except ValueError:
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me video files (either as a native video/animation or as a document like .mp4/.mkv). "
        "I'll detect each video's duration, add it to this chat's running total, and reply with the updated total.\n\n"
        "Commands:\n"
        "/total - show current total for this chat\n"
        "/reset - reset the running total for this chat"
    )


async def total_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    total = chat_totals.get(chat_id, 0)
    await update.message.reply_text(f"Current total: {human_readable_seconds(total)} ({total} seconds)")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_totals[chat_id] = 0
    await update.message.reply_text("Running total reset to 0.")


async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles native Telegram Video messages (update.message.video),
    and Animations (GIFs) which also provide duration metadata.
    """
    msg = update.message
    chat_id = update.effective_chat.id
    added = 0
    details = []

    # Video
    if msg.video:
        dur = msg.video.duration or 0
        if dur:
            added += int(dur)
            details.append(("video", dur, msg.video.file_name or "video"))
    # Animation (e.g., animated GIF) - has duration
    if msg.animation:
        dur = msg.animation.duration or 0
        if dur:
            added += int(dur)
            details.append(("animation", dur, msg.animation.file_name or "animation"))

    if added == 0:
        await msg.reply_text("Couldn't detect duration from the provided video/animation metadata.")
        return

    chat_totals[chat_id] = chat_totals.get(chat_id, 0) + int(added)

    # Build reply
    lines = []
    for typ, dur, name in details:
        lines.append(f"Found {typ} ({name}) → {human_readable_seconds(int(dur))}")

    lines.append(f"\nAdded: {human_readable_seconds(int(added))}")
    lines.append(f"New total: {human_readable_seconds(chat_totals[chat_id])} ({chat_totals[chat_id]} seconds)")

    await msg.reply_text("\n".join(lines))


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle documents. If the document looks like a video (mime-type or extension),
    download and probe with ffprobe.
    """
    msg = update.message
    doc = msg.document
    chat_id = update.effective_chat.id

    if not doc:
        await msg.reply_text("No document found in message.")
        return

    filename = (doc.file_name or "").lower()
    mime = (doc.mime_type or "").lower()

    looks_like_video = False
    if mime.startswith("video/"):
        looks_like_video = True
    else:
        for ext in VIDEO_EXTENSIONS:
            if filename.endswith(ext):
                looks_like_video = True
                break

    if not looks_like_video:
        await msg.reply_text("This document doesn't look like a video file (based on mime-type/extension). Send a video file and I'll measure its duration.")
        return

    await msg.reply_text(f"Downloading {doc.file_name or 'file'} and probing duration (ffprobe)...")

    # Download file
    file = await doc.get_file()
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, doc.file_name or "video.bin")
        try:
            # download_to_drive available on python-telegram-bot; fallback to download
            await file.download_to_drive(custom_path=local_path)
        except Exception:
            try:
                await file.download(custom_path=local_path)
            except Exception as e:
                await msg.reply_text(f"Failed to download file: {e}")
                return

        duration = get_duration_with_ffprobe(local_path)
        if duration is None:
            await msg.reply_text(
                "Could not determine duration. This usually means ffprobe (ffmpeg) is not installed or the file format is unsupported.\n"
                "Install ffmpeg and ensure ffprobe is available in PATH, then try again."
            )
            return

        added = int(duration)
        chat_totals[chat_id] = chat_totals.get(chat_id, 0) + added

        await msg.reply_text(
            f"Found {human_readable_seconds(added)} ({added} seconds) in {doc.file_name}.\n"
            f"New total: {human_readable_seconds(chat_totals[chat_id])} ({chat_totals[chat_id]} seconds)"
        )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video (native video or a video file as a document) and I'll add its duration to this chat's total. Use /total to see the sum or /reset to clear it.")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN environment variable and restart.")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("total", total_command))
    app.add_handler(CommandHandler("reset", reset_command))

    # Video / animation messages
    app.add_handler(MessageHandler(filters.Video.ALL | filters.ANIMATION, handle_video_message))
    # Documents (some videos are sent as documents)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Fallback
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot starting (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
