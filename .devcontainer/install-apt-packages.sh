#!/bin/sh

set -eu

if [ "$#" -eq 0 ]; then
    echo "usage: $0 PACKAGE..." >&2
    exit 2
fi

# Only acquisition is retried. Running dpkg again could hide an installation
# failure or repeat package maintainer scripts after a partial installation.
retry_acquisition() {
    phase=$1
    shift
    attempt=1
    while :; do
        printf 'APT [%s] %s: attempt %s/6\n' \
            "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "$attempt" >&2
        # Bound the entire command as HTTP timeouts do not cover every stall.
        # The outer loop owns retries, including HTTP 503/504 responses.
        if timeout --kill-after=15s 300 \
            apt-get -o Acquire::Retries=0 \
                -o Acquire::http::Timeout=60 \
                -o Acquire::https::Timeout=60 "$@"; then
            return 0
        else
            acquisition_status=$?
        fi

        if [ "$attempt" -ge 6 ]; then
            printf 'ERROR: APT %s failed after 6 attempts (exit %s).\n' \
                "$phase" "$acquisition_status" >&2
            return "$acquisition_status"
        fi

        delay=$((attempt * 10))
        printf 'WARN: APT %s failed (exit %s); retrying in %s seconds.\n' \
            "$phase" "$acquisition_status" "$delay" >&2
        sleep "$delay"
        attempt=$((attempt + 1))
    done
}

export DEBIAN_FRONTEND=noninteractive
retry_acquisition 'index update' -o APT::Update::Error-Mode=any update
retry_acquisition 'package download' install -y --no-install-recommends \
    --allow-downgrades --download-only "$@"

printf 'APT [%s] installing downloaded packages\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >&2
apt-get install -y --no-install-recommends --allow-downgrades --no-download "$@"
