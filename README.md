
# 📖 README – YouTube Playlist/Video → MP3 Downloader (with TXT Report)

## ⚠️ Disclaimer
Use this script **only** for content you own the rights to download, or that is licensed for free reuse.  
Downloading copyrighted material without permission may violate the law and YouTube's Terms of Service.

---

## 🎵 Features
- Works with both **YouTube playlists** and **single videos** (auto-detected)
- Download as **MP3** files with high quality
- **Audio quality:** MP3 **V0** (VBR ~245 kbps, transparent quality)
- **No images** are saved or embedded
- **No numbering** in filenames: files are named as:
  ```
  Title [VIDEOID].mp3
  ```
- Automatically creates a **folder with the playlist/video title** next to the script
- Maintains a `.downloaded.txt` archive to avoid re-downloading items
- Adds a small **sleep between downloads** (yt-dlp default) to reduce rate-limit risks
- Shows **per-item progress percentage** during download
- Generates a human-readable **TXT report** named `000_report_YYYY-MM-DD_HH-MM-SS.txt` inside the output folder

---

## 🖥️ Requirements
- **Python 3.8+**
- **yt-dlp**
- **ffmpeg** available on your system `PATH`

Install the Python dependency:
```bash
pip install yt-dlp
```

### Install ffmpeg
- **Windows:**  
  1. Download the “essentials build” from https://www.gyan.dev/ffmpeg/builds/  
  2. Extract to `C:\ffmpeg\`  
  3. Add `C:\ffmpeg\bin` to your system PATH  
  4. Restart your terminal

- **Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install ffmpeg
```

- **macOS (Homebrew):**
```bash
brew install ffmpeg
```

---

## ▶️ Usage
Run the script without arguments:
```bash
python download_youtube_playlist_mp3.py
```

It will ask for a playlist or video URL:
```
Paste the YouTube playlist or video URL:
```

Example output:
```
Target: My Playlist (playlist)
Output folder: C:\Users\you\Desktop\My Playlist
Mode: MP3 (V0, high quality)
```

or for a single video:
```
Target: My Song (single video)
Output folder: C:\Users\you\Desktop\My Song
Mode: MP3 (V0, high quality)
```

At the end you'll find the `.mp3` files in the output folder and a TXT report named like:
```
000_report_2025-09-07_21-47-06.txt
```

---

## Notes
- Converting to MP3 is **lossy**; V0 is widely considered audibly transparent while keeping file size efficient.
- If you ever want **CBR 320 kbps**, replace `postprocessor_args` with `['-b:a', '320k']` in the script.
