#!/bin/sh

set -eu

temporary_directory=$(mktemp -d)
cleanup() {
    rm -rf -- "$temporary_directory"
}
trap cleanup EXIT HUP INT TERM

npm view @devcontainers/cli time --json > "$temporary_directory/release-times.json"
version=$(
    node - "$temporary_directory/release-times.json" <<'NODE'
const fs = require("fs");

const releaseTimes = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const cutoff = Date.now() - 14 * 24 * 60 * 60 * 1000;
const semanticVersion = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/;

const eligible = Object.entries(releaseTimes)
  .map(([version, publishedAt]) => {
    const match = semanticVersion.exec(version);
    const timestamp = Date.parse(publishedAt);
    return match && Number.isFinite(timestamp) && timestamp <= cutoff
      ? { version, parts: match.slice(1).map(Number) }
      : null;
  })
  .filter(Boolean)
  .sort((left, right) => {
    for (let index = 0; index < 3; index += 1) {
      if (left.parts[index] !== right.parts[index]) {
        return right.parts[index] - left.parts[index];
      }
    }
    return 0;
  });

if (eligible.length === 0) {
  console.error("No Dev Containers CLI release has completed the 14-day waiting period.");
  process.exit(1);
}
process.stdout.write(eligible[0].version);
NODE
)

cleanup
trap - EXIT HUP INT TERM
printf 'Using @devcontainers/cli %s (published at least 14 days ago)\n' "$version" >&2
exec npx --yes "@devcontainers/cli@$version" "$@"
