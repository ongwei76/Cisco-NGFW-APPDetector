#!/usr/bin/env bash
# Builds release binaries into dist/. Requires Go 1.22+.
set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(sed -n 's/.*Version *= *"\(.*\)".*/\1/p' internal/version/version.go)
OUT=dist
rm -rf "$OUT"
mkdir -p "$OUT"

go vet ./...
go test ./...

targets=(
  "windows amd64 .exe"
  "darwin arm64 "
  "darwin amd64 "
  "linux amd64 "
)
for t in "${targets[@]}"; do
  read -r os arch ext <<<"$t"
  name="ngfw-lua-importer-${VERSION}-${os}-${arch}${ext}"
  echo "building $name"
  CGO_ENABLED=0 GOOS=$os GOARCH=$arch go build -trimpath -ldflags "-s -w" -o "$OUT/$name" .
done

(cd "$OUT" && shasum -a 256 ngfw-lua-importer-* > SHA256SUMS.txt)
ls -lh "$OUT"
