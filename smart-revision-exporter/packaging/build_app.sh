#!/bin/bash
# Build "Smart Revision Exporter.app" (Apple Silicon, local development build).
#
#   ./packaging/build_app.sh            # build into ./dist
#   ./packaging/build_app.sh --install  # also copy to /Applications
#
# Requirements: macOS 13+, Xcode or Command Line Tools (Swift 5.9+), Python 3.9+.
# The app is ad-hoc signed only.  It is NOT notarized; Gatekeeper will ask for
# confirmation on first launch (right-click > Open).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Smart Revision Exporter"
DIST="$ROOT/dist"
APP="$DIST/$APP_NAME.app"
VERSION="$(python3 -c "import sys; sys.path.insert(0, '$ROOT/engine'); import srx; print(srx.__version__)")"
BUILD="$(date +%Y%m%d%H%M)"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "error: the macOS application can only be built on macOS" >&2
  exit 1
fi
if ! command -v swift >/dev/null; then
  echo "error: Swift toolchain not found. Install Xcode or run: xcode-select --install" >&2
  exit 1
fi

echo "==> Engine self-check (unit tests, no media)"
python3 -m srx --version >/dev/null 2>&1 || true
(cd "$ROOT/engine" && python3 -c "import srx.cli, srx.exporter, srx.verify, srx.resolve_bridge; print('engine imports OK')")

echo "==> Swift unit tests (SRXCore)"
(cd "$ROOT/app" && swift test)

echo "==> Building arm64 release"
(cd "$ROOT/app" && swift build -c release --arch arm64)
BIN="$(cd "$ROOT/app" && swift build -c release --arch arm64 --show-bin-path)/SmartRevisionExporter"

echo "==> Assembling $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/engine"
cp "$BIN" "$APP/Contents/MacOS/SmartRevisionExporter"
sed -e "s/__VERSION__/$VERSION/" -e "s/__BUILD__/$BUILD/" "$ROOT/packaging/Info.plist" > "$APP/Contents/Info.plist"
cp "$ROOT/packaging/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
# engine (pure Python package, no compiled code)
rsync -a --exclude "__pycache__" --exclude "*.pyc" "$ROOT/engine/srx" "$APP/Contents/Resources/engine/"
cp "$ROOT/docs/USER_GUIDE.md" "$APP/Contents/Resources/" 2>/dev/null || true
echo "$VERSION ($BUILD) local development build" > "$APP/Contents/Resources/BUILD_INFO.txt"

echo "==> Ad-hoc code signature (local use only)"
codesign --force --deep --sign - "$APP"
codesign --verify --verbose=1 "$APP"
lipo -info "$APP/Contents/MacOS/SmartRevisionExporter"

if [[ "${1:-}" == "--install" ]]; then
  echo "==> Installing to /Applications"
  rm -rf "/Applications/$APP_NAME.app"
  cp -R "$APP" "/Applications/"
fi

echo
echo "Built: $APP"
echo "Version $VERSION, build $BUILD - LOCAL DEVELOPMENT BUILD (ad-hoc signed, not notarized)."
