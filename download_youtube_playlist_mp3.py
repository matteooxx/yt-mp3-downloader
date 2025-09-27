#!/usr/bin/env python3
"""
YouTube Playlist/Video → MP3 Downloader (TXT Report, Auto-Detect)
------------------------------------------------------------------
- Paste either a YouTube **playlist** URL or a **single video** URL.
- Creates an output folder named after the playlist or the video (auto-detected).
- Always downloads MP3 (V0 quality).
- Filenames: "Title [VIDEOID].mp3" (no numbering, no images).
- Generates a final TXT report with per-item status and reason (prefixed with 000_).
- Shows per-item progress percentage.
"""

import sys
import re
from datetime import datetime
from pathlib import Path

try:
    import yt_dlp as ytdlp
except ImportError:
    print("Error: yt-dlp is not installed. Run: pip install yt-dlp", file=sys.stderr)
    sys.exit(1)


# --- Utilities ---
def sanitize_for_fs(name: str) -> str:
    name = name.strip().replace("\n", " ").replace("\r", " ")
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip()


class CaptureLogger:
    """Custom logger to capture yt-dlp messages and infer skip/fail reasons."""
    def __init__(self, prefix=""):
        self.prefix = prefix
        self.messages = []
        self.last_level = None
        self.last_message = ""

    def debug(self, msg):   self._push("DEBUG", msg)
    def info(self, msg):    self._push("INFO", msg)
    def warning(self, msg): self._push("WARNING", msg)
    def error(self, msg):   self._push("ERROR", msg)

    def _push(self, level, msg):
        s = str(msg)
        self.messages.append((level, s))
        self.last_level = level
        self.last_message = s


def get_info(url: str):
    with ytdlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        return ydl.extract_info(url, download=False)


def _fmt_bytes(n):
    units = ["B","KB","MB","GB","TB"]
    i = 0
    while n >= 1024 and i < len(units)-1:
        n /= 1024.0
        i += 1
    return f"{n:.1f} {units[i]}"


def progress_hook(d):
    status = d.get('status')
    if status == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        downloaded = d.get('downloaded_bytes') or 0
        pct = (downloaded / total * 100) if total else 0.0
        speed = d.get('speed') or 0
        eta = d.get('eta')
        line = (f"      Progress: {pct:6.2f}% "
                f"({_fmt_bytes(downloaded)} / {_fmt_bytes(total) if total else '??'}) "
                f"at {_fmt_bytes(speed)}/s  ETA: {eta if eta is not None else '-'}")
        print("\r" + line, end="", flush=True)
    elif status == 'finished':
        print("\r      Progress: 100.00% (download complete)                    ")
        print("      Converting to MP3 (V0)...")


def build_ydl_opts(out_dir: Path, logger: CaptureLogger):
    outtmpl = str(out_dir / "%(title)s [%(id)s].%(ext)s")
    return {
        # Prefer m4a (commonly available as high-quality audio on YouTube),
        # fall back to best audio, then best overall.
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': outtmpl,
        'ignoreerrors': True,
        'prefer_ffmpeg': True,
        'download_archive': str(out_dir / ".downloaded.txt"),
        'concurrent_fragment_downloads': 5,
        'retries': 10,
        'fragment_retries': 10,
        # Allow yt-dlp to try formats that may be marked unplayable as a fallback
        # (can help when YouTube forces newer streaming clients / SABR).
        'allow_unplayable_formats': True,
    # Force a different YouTube player client when extracting (helps when
    # YouTube is forcing SABR/web-only formats). This mirrors
    # --extractor-args "youtube:player_client=android" behavior.
    'extractor_args': {'youtube': {'player_client': 'android'}},
        'windowsfilenames': True,
        'writethumbnail': False,  # no images
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '0'},  # V0
            {'key': 'FFmpegMetadata'},
        ],
        'postprocessor_args': ['-q:a', '0'],
        'progress_hooks': [progress_hook],
        'logger': logger,
    }


def find_mp3_by_id(folder: Path, vid: str):
    """Return the MP3 file that ends with ' [ID].mp3' (case-insensitive), or None."""
    if not vid:
        return None
    target_suffix = f" [{vid}].mp3".lower()
    for p in folder.glob("*.mp3"):
        if p.name.lower().endswith(target_suffix):
            return p
    return None


def last_reason_from_logs(logger: CaptureLogger) -> str:
    """Try to infer a readable reason from yt-dlp logs."""
    for lvl, msg in reversed(logger.messages):
        low = msg.lower()
        if "has already been recorded in archive" in msg:
            return "Already downloaded (download_archive)"
        if "private" in low:
            return "Private video"
        if "unavailable" in low or "not available" in low:
            return "Video unavailable"
        if "copyright" in low:
            return "Blocked due to copyright"
        if "sign in" in low or "consent" in low:
            return "Sign-in/consent required"
        if "http error 410" in low or "http error 404" in low:
            return "Invalid or removed URL"
        if lvl == "ERROR":
            return msg
    return "Unknown"


def main():
    url = input("Paste the YouTube playlist or video URL: ").strip()
    if not url:
        print("No URL provided. Exiting.")
        return

    base_dir = Path(__file__).parent.resolve()

    try:
        info = get_info(url)
    except Exception as e:
        print(f"Failed to extract info: {e}")
        return

    # Detect playlist vs single video
    raw_entries = info.get("entries")
    if raw_entries:
        entries = [e for e in raw_entries if e]
        collection_type = "playlist"
        default_title = "Untitled_Playlist"
    else:
        entries = [info]
        collection_type = "single"
        default_title = "Untitled_Video"

    collection_title = sanitize_for_fs(info.get("title") or default_title)
    out_dir = base_dir / collection_title
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nTarget: {collection_title} ({'playlist' if collection_type=='playlist' else 'single video'})")
    print(f"Output folder: {out_dir}")
    print("Mode: MP3 (V0, high quality)\n")

    if not entries:
        print("No items found or unable to read entries.")
        return

    results = []
    total_ok = total_fail = total_skip = 0

    for idx, e in enumerate(entries, 1):
        vid = e.get('id')
        title = e.get('title') or f"ID_{vid or idx}"
        video_url = e.get('url') or e.get('webpage_url') or (f"https://www.youtube.com/watch?v={vid}" if vid else None)

        if not video_url:
            results.append({"index": idx, "id": vid, "title": title,
                            "status": "fail", "reason": "URL missing in entry"})
            total_fail += 1
            print(f"[{idx}/{len(entries)}] {title}  →  FAILED (missing URL)")
            continue

        logger = CaptureLogger(prefix=f"[{idx}] ")
        ydl_opts = build_ydl_opts(out_dir, logger)

        print(f"[{idx}/{len(entries)}] Downloading: {title}")

        pre_existing = (find_mp3_by_id(out_dir, vid) is not None) if vid else False

        try:
            # Primary download attempt
            with ytdlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            mp3_path = find_mp3_by_id(out_dir, vid) if vid else None
            if mp3_path:
                if pre_existing or any("has already been recorded in archive" in m for _, m in logger.messages):
                    results.append({"index": idx, "id": vid, "title": title,
                                    "status": "skipped", "reason": "Already downloaded (download_archive)"})
                    total_skip += 1
                    print("   ↳ SKIPPED (already present)")
                else:
                    results.append({"index": idx, "id": vid, "title": title,
                                    "status": "success", "reason": "OK"})
                    total_ok += 1
                    print("   ↳ OK")
            else:
                reason = last_reason_from_logs(logger)
                status = "skipped" if "Already downloaded" in reason else "fail"
                if status == "skipped":
                    total_skip += 1
                else:
                    total_fail += 1
                results.append({"index": idx, "id": vid, "title": title,
                                "status": status, "reason": reason})
                print(f"   ↳ {status.upper()}: {reason}")

        except Exception as ex:
            # If the failure looks like SABR / format-unavailable (only images,
            # requested format missing, signature extraction), try a single
            # retry with an alternate extractor arg form and a broader format.
            msg = str(ex)
            retried = False
            if any(k in msg for k in ("Only images are available", "Requested format is not available", "Signature extraction failed")):
                retried = True
                fb_logger = CaptureLogger(prefix=logger.prefix + "FALLBACK ")
                fb_opts = dict(ydl_opts)
                # Use string-style extractor args as an alternative and
                # fall back to best audio if m4a wasn't available.
                fb_opts['extractor_args'] = {'youtube': 'player_client=android'}
                fb_opts['format'] = 'bestaudio/best'
                fb_opts['logger'] = fb_logger
                try:
                    with ytdlp.YoutubeDL(fb_opts) as ydl:
                        ydl.download([video_url])

                    mp3_path = find_mp3_by_id(out_dir, vid) if vid else None
                    if mp3_path:
                        results.append({"index": idx, "id": vid, "title": title,
                                        "status": "success", "reason": "OK (fallback)"})
                        total_ok += 1
                        print("   ↳ OK (fallback)")
                        # merge fallback logs into main logger for reporting
                        logger.messages.extend(fb_logger.messages)
                        continue
                except Exception as ex2:
                    # merge fallback logs and fall through to final failure
                    logger.messages.extend(fb_logger.messages)
                    msg = str(ex2)

            total_fail += 1
            reason_text = msg if not retried else (msg + " (fallback attempted)")
            results.append({"index": idx, "id": vid, "title": title,
                            "status": "fail", "reason": reason_text})
            print(f"   ↳ FAILED: {reason_text}")

    # TXT Report with 000_ prefix
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    txt_path = out_dir / f"000_report_{timestamp}.txt"

    with txt_path.open("w", encoding="utf-8") as tf:
        for r in results:
            tf.write(f"[{r.get('index')}] {r.get('title')} [{r.get('id')}]  →  {r.get('status').upper()} ({r.get('reason')})\n")
        tf.write("\n=== SUMMARY ===\n")
        tf.write(f"Total items: {len(results)}\n")
        tf.write(f"  ✓ Success: {total_ok}\n")
        tf.write(f"  → Skipped: {total_skip}\n")
        tf.write(f"  ✗ Failed:  {total_fail}\n")

    print("\n=== FINAL REPORT ===")
    print(f"Total items: {len(results)}")
    print(f"  ✓ Success: {total_ok}")
    print(f"  → Skipped: {total_skip}")
    print(f"  ✗ Failed:  {total_fail}")
    print(f"\nReport saved to: {txt_path}")


if __name__ == "__main__":
    main()
