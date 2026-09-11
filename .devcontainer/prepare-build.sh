#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
timestamp_file="$script_dir/.build-resolution-time"
temporary_file="$timestamp_file.tmp"

cleanup() {
    rm -f -- "$temporary_file"
}
trap cleanup EXIT HUP INT TERM

umask 022
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$temporary_file"
mv -f -- "$temporary_file" "$timestamp_file"
trap - EXIT HUP INT TERM
