"""yt2mp3 — a local YouTube-to-MP3 downloader with Spotify playlist support.

Run:  ./venv/bin/python app.py   (then open http://127.0.0.1:5000)
"""
import csv
import io
import json
import os
import queue
import sys
import tempfile
import threading
import uuid
import zipfile

from flask import (
    Flask,
    Response,
    abort,
    after_this_request,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)
import yt_dlp

if getattr(sys, "frozen", False):
    # Running inside the packaged Mac app: resources live in the bundle,
    # which is read-only, so save MP3s to ~/Downloads/yt2mp3 instead.
    BASE_DIR = sys._MEIPASS
    DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "yt2mp3")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Optional explicit ffmpeg path (set by the Mac app launcher); otherwise
# yt-dlp looks for ffmpeg on PATH.
FFMPEG_LOCATION = os.environ.get("YT2MP3_FFMPEG")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

# In-memory job registry. Each job streams progress events to the browser
# over Server-Sent Events while a worker thread downloads items one by one.
jobs = {}
jobs_lock = threading.Lock()


class Job:
    def __init__(self, items, numbered=False):
        self.id = uuid.uuid4().hex
        # Prefix filenames with a 3-digit index (playlists only) so order
        # survives when copied to an MP3 device that sorts by filename.
        self.numbered = numbered
        # items: list of {"query": str, "label": str}
        self.items = [
            {
                "index": i,
                "label": it["label"],
                "query": it["query"],
                "status": "queued",
                "progress": 0,
                "filename": None,
                "error": None,
            }
            for i, it in enumerate(items)
        ]
        self.events = queue.Queue()
        self.done = False

    def emit(self, event):
        self.events.put(event)


def _ydl_opts(progress_hook, prefix=""):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, prefix + "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "default_search": "ytsearch",
    }
    if FFMPEG_LOCATION:
        opts["ffmpeg_location"] = FFMPEG_LOCATION
    return opts


def _download_item(job, item):
    """Download a single item (URL or 'ytsearch1:...' query) as MP3."""
    captured = {"title": None, "filepath": None}

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            pct = int(downloaded * 100 / total) if total else 0
            item["progress"] = pct
            if d.get("info_dict", {}).get("title"):
                captured["title"] = d["info_dict"]["title"]
            job.emit(
                {
                    "type": "progress",
                    "index": item["index"],
                    "progress": pct,
                    "title": captured["title"],
                }
            )
        elif d["status"] == "finished":
            # Download done; ffmpeg conversion to mp3 happens next.
            captured["filepath"] = d.get("filename")
            item["progress"] = 100
            job.emit(
                {
                    "type": "converting",
                    "index": item["index"],
                    "title": captured["title"],
                }
            )

    item["status"] = "downloading"
    job.emit({"type": "status", "index": item["index"], "status": "downloading"})

    prefix = f"{item['index']:03d}-" if job.numbered else ""
    with yt_dlp.YoutubeDL(_ydl_opts(hook, prefix)) as ydl:
        info = ydl.extract_info(item["query"], download=True)
        # For search queries yt-dlp returns a playlist-like result.
        if info.get("_type") == "playlist" or "entries" in info:
            info = info["entries"][0]
        captured["title"] = info.get("title", captured["title"])
        base = ydl.prepare_filename(info)

    mp3_path = os.path.splitext(base)[0] + ".mp3"
    filename = os.path.basename(mp3_path)
    item["filename"] = filename
    item["status"] = "done"
    job.emit(
        {
            "type": "done",
            "index": item["index"],
            "title": captured["title"],
            "filename": filename,
        }
    )


def _run_job(job):
    for item in job.items:
        try:
            _download_item(job, item)
        except Exception as e:  # noqa: BLE001 - surface any failure to the UI
            item["status"] = "error"
            item["error"] = str(e)
            job.emit(
                {"type": "error", "index": item["index"], "error": str(e)}
            )
    job.done = True
    job.emit({"type": "complete"})


def _start_job(items, numbered=False):
    job = Job(items, numbered=numbered)
    with jobs_lock:
        jobs[job.id] = job
    threading.Thread(target=_run_job, args=(job,), daemon=True).start()
    return job


def _parse_spotify_csv(text):
    """Parse a Spotify/Exportify CSV into search queries.

    Tolerant of column naming: looks for a track-name column and an
    artist column by fuzzy header matching.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    def find(*keywords):
        for f in reader.fieldnames:
            low = f.lower()
            if all(k in low for k in keywords):
                return f
        return None

    track_col = find("track", "name") or find("track") or find("title") or find("name")
    artist_col = find("artist")

    items = []
    for row in reader:
        track = (row.get(track_col) or "").strip() if track_col else ""
        artist = (row.get(artist_col) or "").strip() if artist_col else ""
        if not track and not artist:
            continue
        # Artist columns sometimes hold multiple names separated by commas.
        artist = artist.split(",")[0].strip() if artist else ""
        label = f"{artist} - {track}".strip(" -") if artist else track
        query = f"ytsearch1:{artist} {track} audio".strip()
        items.append({"label": label, "query": query})
    return items


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/youtube", methods=["POST"])
def api_youtube():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    job = _start_job([{"label": url, "query": url}])
    return jsonify({"job_id": job.id, "items": _public_items(job)})


@app.route("/api/playlist", methods=["POST"])
def api_playlist():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    raw = request.files["file"].read().decode("utf-8-sig", errors="replace")
    items = _parse_spotify_csv(raw)
    if not items:
        return jsonify({"error": "No tracks found in CSV"}), 400
    job = _start_job(items, numbered=True)
    return jsonify({"job_id": job.id, "items": _public_items(job)})


def _public_items(job):
    return [
        {
            "index": it["index"],
            "label": it["label"],
            "status": it["status"],
            "progress": it["progress"],
            "filename": it["filename"],
            "error": it["error"],
        }
        for it in job.items
    ]


@app.route("/api/stream/<job_id>")
def api_stream(job_id):
    job = jobs.get(job_id)
    if not job:
        abort(404)

    def gen():
        while True:
            try:
                event = job.events.get(timeout=30)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "complete":
                break

    return Response(gen(), mimetype="text/event-stream")


@app.route("/file/<path:filename>")
def file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


def write_job_zip(job_id, dest):
    """Write every completed track of a job into a zip at `dest`.

    Returns the number of tracks written, or None if the job doesn't exist.
    """
    job = jobs.get(job_id)
    if not job:
        return None
    files = [
        it["filename"]
        for it in job.items
        if it["status"] == "done" and it["filename"]
    ]
    count = 0
    # MP3s are already compressed, so store (don't re-compress) for speed.
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_STORED) as zf:
        for fn in files:
            path = os.path.join(DOWNLOAD_DIR, fn)
            if os.path.exists(path):
                zf.write(path, arcname=fn)
                count += 1
    return count


@app.route("/api/zip/<job_id>")
def api_zip(job_id):
    """Bundle every completed track of a job into a single zip download."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    count = write_job_zip(job_id, tmp.name)
    if not count:
        os.remove(tmp.name)
        abort(404, "No completed downloads to zip")

    @after_this_request
    def _cleanup(response):
        try:
            os.remove(tmp.name)
        except OSError:
            pass
        return response

    return send_file(
        tmp.name,
        as_attachment=True,
        download_name="yt2mp3_playlist.zip",
        mimetype="application/zip",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False)
