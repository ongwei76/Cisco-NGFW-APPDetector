#!/usr/bin/env bash
# Builds release files into dist/. Requires Go 1.22+; the macOS app needs macOS (lipo, codesign, ditto).
set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(sed -n 's/.*Version *= *"\(.*\)".*/\1/p' internal/version/version.go)
OUT=dist
rm -rf "$OUT"
mkdir -p "$OUT"

go vet ./...
go test ./...

build() { # os arch output
  echo "building $3"
  CGO_ENABLED=0 GOOS=$1 GOARCH=$2 go build -trimpath -ldflags "-s -w" -o "$3" .
}

build windows amd64 "$OUT/ngfw-lua-importer-${VERSION}-windows-x64.exe"
build linux amd64 "$OUT/ngfw-lua-importer-${VERSION}-linux-x64"

# macOS: one universal (Apple silicon + Intel) .app, zipped so the bundle and execute bits survive download.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
build darwin arm64 "$TMP/arm64"
build darwin amd64 "$TMP/amd64"
APP="$TMP/NGFW Lua Importer.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
lipo -create -output "$APP/Contents/MacOS/ngfw-lua-importer" "$TMP/arm64" "$TMP/amd64"
sed "s/__VERSION__/$VERSION/g" packaging/macos/Info.plist > "$APP/Contents/Info.plist"
cp packaging/macos/AppIcon.icns "$APP/Contents/Resources/"
codesign --force --sign - "$APP" # ad-hoc signature; not notarized (see README)
codesign --verify --strict "$APP"
ditto -c -k --keepParent "$APP" "$OUT/ngfw-lua-importer-${VERSION}-macos-universal.zip"

(cd "$OUT" && shasum -a 256 ngfw-lua-importer-* > SHA256SUMS.txt)
ls -lh "$OUT"
