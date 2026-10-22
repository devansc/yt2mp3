#!/bin/bash
# Build standalone Mac apps + DMGs.
# Usage: ./build_mac.sh [arm|intel|all]   (default: arm)
#   arm   -> dist/yt2mp3-AppleSilicon.dmg  (M1 and later)
#   intel -> dist/yt2mp3-Intel.dmg         (built under Rosetta)
set -euo pipefail
cd "$(dirname "$0")"

build() {
  local arch=$1 label=$2 python=$3
  local venv=build/venv-$arch out=dist/$arch

  echo "==> Building $label ($arch)"
  [ -x "$venv/bin/python" ] || "$python" -m venv "$venv"
  # Always grab the newest yt-dlp so the app ships with a current YouTube engine.
  "$venv/bin/pip" install -q -U pip flask yt-dlp pyinstaller pywebview imageio-ffmpeg

  # Self-contained ffmpeg for this arch (Homebrew's depends on brew-only libraries).
  local ffmpeg_src
  ffmpeg_src=$("$venv/bin/python" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
  mkdir -p "build/bin-$arch"
  cp "$ffmpeg_src" "build/bin-$arch/ffmpeg"
  chmod +x "build/bin-$arch/ffmpeg"

  rm -rf "$out" "dist/yt2mp3-$label.dmg"
  "$venv/bin/pyinstaller" --noconfirm --clean --windowed \
    --name yt2mp3 \
    --target-arch "$arch" \
    --osx-bundle-identifier com.yt2mp3.app \
    --icon "$PWD/assets/icon.icns" \
    --add-data "$PWD/templates:templates" \
    --add-binary "$PWD/build/bin-$arch/ffmpeg:bin" \
    --collect-submodules yt_dlp \
    --workpath "build/pyinstaller-$arch" --distpath "$out" --specpath "build/spec-$arch" \
    mac_app.py

  # DMG with the usual "drag to Applications" layout.
  local stage=build/dmg-$arch
  rm -rf "$stage" && mkdir -p "$stage"
  cp -R "$out/yt2mp3.app" "$stage/"
  ln -s /Applications "$stage/Applications"
  hdiutil create -volname yt2mp3 -srcfolder "$stage" -ov -format UDZO "dist/yt2mp3-$label.dmg"
  echo "==> Built dist/yt2mp3-$label.dmg"
}

intel_python() {
  # Standalone x86_64 Python (Homebrew's is arm64-only; Apple's is too old).
  local py=build/py-x86_64/python/bin/python3
  if [ ! -x "$py" ]; then
    local url
    # Authenticate when a token is available (CI) to avoid API rate limits.
    local auth=()
    [ -n "${GH_TOKEN:-}" ] && auth=(-H "Authorization: Bearer $GH_TOKEN")
    url=$(curl -s ${auth[@]+"${auth[@]}"} https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest |
      python3 -c "import sys, json
for a in json.load(sys.stdin)['assets']:
    n = a['name']
    if n.startswith('cpython-3.12.') and n.endswith('x86_64-apple-darwin-install_only.tar.gz'):
        print(a['browser_download_url']); break")
    mkdir -p build/py-x86_64
    curl -sL "$url" | tar xz -C build/py-x86_64
  fi
  echo "$py"
}

case "${1:-arm}" in
  arm)   build arm64 AppleSilicon python3 ;;
  intel) build x86_64 Intel "$(intel_python)" ;;
  all)   build arm64 AppleSilicon python3; build x86_64 Intel "$(intel_python)" ;;
  *)     echo "usage: $0 [arm|intel|all]"; exit 1 ;;
esac
