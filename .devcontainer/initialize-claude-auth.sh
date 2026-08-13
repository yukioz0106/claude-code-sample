#!/bin/sh
set -eu

workspace=${1:-/workspace}
template="$workspace/.claude/settings.local.json.template"
target="$workspace/.claude/settings.local.json"

if [ ! -e "$target" ]; then
  cp "$template" "$target"
fi

chmod 600 "$target"
