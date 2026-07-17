#!/usr/bin/env bash
# Download and run a standalone springdocker binary (template — archive not published in CI yet).
# Override version: SPRINGDOCKER_VERSION=1.2.0 ./standalone-binary.sh --help
set -euo pipefail

VERSION="${SPRINGDOCKER_VERSION:-1.2.0}"
ARCHIVE_URL="https://github.com/mnafshin/springdocker/releases/download/v${VERSION}/springdocker-linux-amd64.tar.gz"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

curl -fsSL "$ARCHIVE_URL" -o "$tmpdir/springdocker.tar.gz"
tar -xzf "$tmpdir/springdocker.tar.gz" -C "$tmpdir"
exec "$tmpdir/springdocker" "$@"
