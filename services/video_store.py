"""
video_store.py - Saves, lists, deletes and (optionally) converts greeting videos.

The video itself is RECORDED IN THE BROWSER (see static/js/recorder.js).
The browser then uploads a copy here so it appears in the local gallery.
All files stay in the project's output/videos folder.

Optional extras when FFmpeg is installed (not required):
    * inspect_streams() - confirms the file really has a video AND an audio track
    * convert_to_mp4()  - makes an MP4 copy for players that cannot open WebM
"""
import json
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

import config

# Only names that WE generate are accepted. This blocks path tricks such as
# "../../windows/system.ini".
SAFE_NAME_RE = re.compile(r"^greeting_[a-z0-9\-]{1,40}_[0-9]{8}-[0-9]{6}_[a-f0-9]{6}\.(webm|mp4)$")
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"   # every WebM/Matroska file starts with these bytes
MIN_VIDEO_BYTES = 2_000


class VideoError(Exception):
    """Problem with a video file. The message is safe to show to the user."""


def ffmpeg_path():
    return shutil.which("ffmpeg")


def ffprobe_path():
    return shutil.which("ffprobe")


def slugify(text):
    """'Priya Sharma' -> 'priya-sharma' (ASCII only, safe for file names)."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:30] or "greeting"


def is_safe_name(name):
    return bool(name) and SAFE_NAME_RE.match(name) is not None


def safe_path(name):
    """Return the full path for a gallery file, or raise VideoError for bad names."""
    if not is_safe_name(name):
        raise VideoError("Invalid video file name.")
    path = (Path(config.VIDEO_DIR) / name).resolve()
    if path.parent != Path(config.VIDEO_DIR).resolve():
        raise VideoError("Invalid video file name.")
    return path


def save_uploaded_video(file_storage, label=""):
    """Validate and save a WebM uploaded by the browser. Returns gallery info."""
    if file_storage is None:
        raise VideoError("No video file was received.")
    data = file_storage.read()
    if len(data) < MIN_VIDEO_BYTES:
        raise VideoError("The recording is empty or too short. Please record again.")
    if not data.startswith(WEBM_MAGIC):
        raise VideoError("Only WebM videos recorded by this app can be saved.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"greeting_{slugify(label)}_{stamp}_{uuid.uuid4().hex[:6]}.webm"
    path = safe_path(name)
    path.write_bytes(data)

    # Remember the label (e.g. "Birthday for Priya") in a tiny side file.
    # ffprobe runs once here (if installed) and the result is stored too.
    meta = {"label": label[:80], "created": time.time(), "streams": inspect_streams(path)}
    path.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    return describe(path)


def describe(path):
    path = Path(path)
    meta = {}
    meta_file = path.with_suffix(".json")
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except ValueError:
            meta = {}
    stat = path.stat()
    mp4 = path.with_suffix(".mp4")
    return {
        "name": path.name,
        "url": f"/media/videos/{path.name}",
        "label": meta.get("label") or path.stem,
        "size_kb": round(stat.st_size / 1024, 1),
        "created": datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y, %I:%M %p"),
        "mp4_url": f"/media/videos/{mp4.name}" if path.suffix == ".webm" and mp4.exists() else None,
        "streams": meta.get("streams"),
    }


def list_videos():
    """Newest first. Only WebM recordings are listed; MP4 copies appear as links."""
    files = [p for p in Path(config.VIDEO_DIR).glob("greeting_*.webm") if is_safe_name(p.name)]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [describe(p) for p in files]


def delete_video(name):
    path = safe_path(name)
    if not path.exists():
        raise VideoError("That video does not exist.")
    for extra in (path, path.with_suffix(".mp4"), path.with_suffix(".json")):
        if extra.exists():
            extra.unlink()


def inspect_streams(path):
    """Use ffprobe (if installed) to list the streams inside the file.

    Returns {"video": bool, "audio": bool} or None when ffprobe is not installed.
    """
    probe = ffprobe_path()
    if not probe:
        return None
    try:
        out = subprocess.run(
            [probe, "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        types = [s.get("codec_type") for s in json.loads(out.stdout or "{}").get("streams", [])]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    return {"video": "video" in types, "audio": "audio" in types}


def convert_to_mp4(name):
    """Optional: create an MP4 (H.264 + AAC) copy with FFmpeg. Returns its URL."""
    source = safe_path(name)
    if source.suffix != ".webm" or not source.exists():
        raise VideoError("That video does not exist.")
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise VideoError("FFmpeg is not installed, so MP4 conversion is unavailable. "
                         "The WebM video works without it.")
    target = source.with_suffix(".mp4")
    command = [ffmpeg, "-y", "-loglevel", "error", "-i", str(source),
               "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
               "-r", "30", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(target)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as exc:
        raise VideoError("MP4 conversion took too long.") from exc
    if result.returncode != 0 or not target.exists():
        raise VideoError("FFmpeg could not convert this video.")
    return f"/media/videos/{target.name}"
