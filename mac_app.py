"""Entry point for the packaged yt2mp3.app (built by build_mac.sh).

Starts the Flask server on a free local port and shows the UI in a native
Mac window (pywebview / WebKit). Closing the window quits the app.
"""
import os
import subprocess
import sys
import threading

# Point yt-dlp at the ffmpeg bundled inside the app before app.py loads.
if getattr(sys, "frozen", False):
    os.environ.setdefault("YT2MP3_FFMPEG", os.path.join(sys._MEIPASS, "bin", "ffmpeg"))

import webview  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import DOWNLOAD_DIR, app, write_job_zip  # noqa: E402


class Api:
    """Native actions the page can call as window.pywebview.api.<name>()."""

    def __init__(self):
        self._window = None

    def open_folder(self):
        subprocess.run(["open", DOWNLOAD_DIR])

    def reveal(self, filename):
        path = os.path.join(DOWNLOAD_DIR, os.path.basename(filename))
        if os.path.exists(path):
            subprocess.run(["open", "-R", path])
        else:
            self.open_folder()

    def save_zip(self, job_id):
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=os.path.expanduser("~/Downloads"),
            save_filename="yt2mp3_playlist.zip",
        )
        if not result:
            return  # cancelled
        dest = result if isinstance(result, str) else result[0]
        if write_job_zip(job_id, dest):
            subprocess.run(["open", "-R", dest])


def main():
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"yt2mp3 running at {url}", flush=True)

    api = Api()
    api._window = webview.create_window(
        "yt2mp3", url, js_api=api, width=760, height=820, min_size=(480, 560)
    )
    webview.start()


if __name__ == "__main__":
    main()
