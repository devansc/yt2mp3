# yt2mp3

A Mac app that turns YouTube videos and Spotify playlists into MP3s. Everything
runs on your own machine — a small Flask app driving
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`.

## Download

| Your Mac | Download |
|---|---|
| Apple Silicon (M1 and later) | [yt2mp3-AppleSilicon.dmg](https://github.com/devansc/yt2mp3/releases/latest/download/yt2mp3-AppleSilicon.dmg) |
| Intel | [yt2mp3-Intel.dmg](https://github.com/devansc/yt2mp3/releases/latest/download/yt2mp3-Intel.dmg) |

Not sure which you have? Apple menu → **About This Mac**. "Chip: Apple M…" means
Apple Silicon; "Processor: Intel" means Intel. Requires macOS 10.15 or later.

**First launch:** the app isn't signed by Apple, so macOS blocks it the first
time. Drag it to Applications, then either:

- run `xattr -cr /Applications/yt2mp3.app` in Terminal, or
- right-click the app → **Open**, then click **Open Anyway** under
  System Settings → Privacy & Security.

MP3s are saved to `~/Downloads/yt2mp3`.

All versions: [Releases](https://github.com/devansc/yt2mp3/releases).

## Features

- **YouTube → MP3** — paste a video link (or type a song name) and get a 192 kbps MP3.
- **Spotify playlist → MP3s** — drop in a playlist CSV; each track is searched on
  YouTube and downloaded one by one, with live per-track progress.
- **Save all as .zip** for playlists, and **Show in Finder** for each track.
- Light and dark mode, following the system setting.

## Spotify playlists

Spotify has no public "download", so this works from the playlist's track list:

1. Go to [exportify.net](https://exportify.net), sign in with Spotify, and click
   **Export** next to the playlist.
2. Drop the CSV into the app's **Spotify playlist** tab.

Any CSV with a header row works as long as it has a track-name column (`Track
Name`, `Track`, `Title` or `Name`) and a column containing `Artist`. Each track
becomes an `Artist Track audio` YouTube search, and the first result is downloaded.
Playlist files are numbered (`001-…`) so they stay in order.

## Run from source

Needs Python 3.10+ and `ffmpeg` on your PATH (`brew install ffmpeg`).

```bash
python3 -m venv venv                      # first time only
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py
```

Then open <http://127.0.0.1:5000>. In this mode MP3s are saved to `downloads/`.

## Docs

- [docs/MAC_APP.md](docs/MAC_APP.md) — how the Mac app is put together and built locally.
- [docs/RELEASING.md](docs/RELEASING.md) — publishing a new version (GitHub Actions)
  and linking to it from a website.

## Troubleshooting

**Downloads fail with `HTTP Error 403: Forbidden` (or similar).** yt-dlp is out of
date — YouTube changed something. From source, update it and restart:

```bash
./venv/bin/pip install -U yt-dlp
```

The Mac app can't update itself; publish a new release (see
[docs/RELEASING.md](docs/RELEASING.md)), which bundles the latest yt-dlp, and
download that.

## Notes

For personal use. Respect YouTube's Terms of Service and copyright law.
