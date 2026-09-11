#!/bin/sh

set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 BUILD_RESOLUTION_TIME_FILE" >&2
    exit 2
fi

resolution_file=$1
if [ ! -s "$resolution_file" ]; then
    echo "build resolution time file is missing or empty: $resolution_file" >&2
    exit 1
fi

resolution_time=$(tr -d '\r\n' < "$resolution_file")
if ! printf '%s\n' "$resolution_time" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'; then
    echo "invalid build resolution time: $resolution_time" >&2
    exit 1
fi

architecture=$(dpkg --print-architecture)
case "$architecture" in
    amd64)
        aws_architecture=x86_64
        claude_platform=linux-x64
        ;;
    arm64)
        aws_architecture=aarch64
        claude_platform=linux-arm64
        ;;
    *)
        echo "unsupported architecture: $architecture" >&2
        exit 1
        ;;
esac

temporary_directory=$(mktemp -d)
cleanup() {
    rm -rf -- "$temporary_directory"
}
trap cleanup EXIT HUP INT TERM

/usr/local/lib/devcontainer/resolve_releases.py \
    --resolution-time "$resolution_time" \
    --architecture "$architecture" \
    --minimum-age-days 14 \
    --output "$temporary_directory/resolved-releases.json"

resolution_epoch=$(date -u -d "$resolution_time" '+%s')
cutoff_epoch=$((resolution_epoch - 14 * 24 * 60 * 60))
snapshot_timestamp=$(date -u -d "@$cutoff_epoch" '+%Y%m%dT%H%M%SZ')

# Disable every non-snapshot APT source inherited from the base image. A
# timestamp with no exact import resolves to the latest earlier import.
rm -f /etc/apt/sources.list
for source_file in /etc/apt/sources.list.d/*; do
    [ -e "$source_file" ] || continue
    rm -f -- "$source_file"
done

cat > /etc/apt/sources.list.d/debian.sources <<EOF
Types: deb
URIs: https://snapshot.debian.org/archive/debian/$snapshot_timestamp/
Suites: bookworm bookworm-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
Check-Valid-Until: no

Types: deb
URIs: https://snapshot.debian.org/archive/debian-security/$snapshot_timestamp/
Suites: bookworm-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
Check-Valid-Until: no
EOF

cat > /etc/apt/preferences.d/devcontainer-snapshot <<'EOF'
Package: *
Pin: origin snapshot.debian.org
Pin-Priority: 1001
EOF

export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=5 update
apt-get -o Acquire::Retries=5 install -y --no-install-recommends --allow-downgrades \
    ca-certificates \
    curl \
    git \
    gnupg \
    groff \
    iputils-ping \
    jq \
    less \
    make \
    unzip \
    vim

download() {
    curl -fsSL \
        --retry 5 \
        --retry-all-errors \
        --retry-delay 1 \
        --connect-timeout 20 \
        --proto '=https' \
        --tlsv1.2 \
        "$1" \
        -o "$2"
}

fingerprint_from_key() {
    key_file=$1
    gpg_home=$2
    gpg --batch \
        --homedir "$gpg_home" \
        --with-colons \
        --import-options show-only \
        --import "$key_file" 2>/dev/null \
        | awk -F: '$1 == "fpr" { print $10; exit }'
}

aws_version=$(jq -er '.aws_cli.version' "$temporary_directory/resolved-releases.json")
aws_url="https://awscli.amazonaws.com/awscli-exe-linux-$aws_architecture-$aws_version.zip"
download "$aws_url" "$temporary_directory/awscliv2.zip"
download "$aws_url.sig" "$temporary_directory/awscliv2.zip.sig"

aws_gpg_home="$temporary_directory/aws-gnupg"
install -d -m 0700 "$aws_gpg_home"
aws_key=/usr/local/lib/devcontainer/aws-cli-public-key.asc
aws_fingerprint=$(fingerprint_from_key "$aws_key" "$aws_gpg_home")
if [ "$aws_fingerprint" != "FB5DB77FD5C118B80511ADA8A6310ACC4672475C" ]; then
    echo "unexpected AWS CLI signing key fingerprint: $aws_fingerprint" >&2
    exit 1
fi
gpg --batch --homedir "$aws_gpg_home" --import "$aws_key"
gpg --batch --homedir "$aws_gpg_home" \
    --verify "$temporary_directory/awscliv2.zip.sig" "$temporary_directory/awscliv2.zip"

unzip -q "$temporary_directory/awscliv2.zip" -d "$temporary_directory/aws-installer"
"$temporary_directory/aws-installer/aws/install" -i /usr/local/aws-cli -b /usr/local/bin
aws_version_output=$(aws --version 2>&1)
case "$aws_version_output" in
    "aws-cli/$aws_version "*) ;;
    *)
        echo "installed AWS CLI version does not match $aws_version: $aws_version_output" >&2
        exit 1
        ;;
esac

claude_version=$(jq -er '.claude_code.version' "$temporary_directory/resolved-releases.json")
claude_base_url="https://downloads.claude.ai/claude-code-releases/$claude_version"
download "https://downloads.claude.ai/keys/claude-code.asc" "$temporary_directory/claude-code.asc"
download "$claude_base_url/manifest.json" "$temporary_directory/claude-manifest.json"
download "$claude_base_url/manifest.json.sig" "$temporary_directory/claude-manifest.json.sig"

claude_gpg_home="$temporary_directory/claude-gnupg"
install -d -m 0700 "$claude_gpg_home"
claude_fingerprint=$(fingerprint_from_key "$temporary_directory/claude-code.asc" "$claude_gpg_home")
if [ "$claude_fingerprint" != "31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE" ]; then
    echo "unexpected Claude Code signing key fingerprint: $claude_fingerprint" >&2
    exit 1
fi
gpg --batch --homedir "$claude_gpg_home" --import "$temporary_directory/claude-code.asc"
gpg --batch --homedir "$claude_gpg_home" \
    --verify "$temporary_directory/claude-manifest.json.sig" "$temporary_directory/claude-manifest.json"

manifest_version=$(jq -er '.version' "$temporary_directory/claude-manifest.json")
if [ "$manifest_version" != "$claude_version" ]; then
    echo "Claude Code manifest version does not match $claude_version: $manifest_version" >&2
    exit 1
fi
claude_checksum=$(jq -er --arg platform "$claude_platform" \
    '.platforms[$platform].checksum | select(test("^[a-f0-9]{64}$"))' \
    "$temporary_directory/claude-manifest.json")
claude_size=$(jq -er --arg platform "$claude_platform" \
    '.platforms[$platform].size | select(type == "number" and . > 0 and floor == .)' \
    "$temporary_directory/claude-manifest.json")
claude_binary_name=$(jq -er --arg platform "$claude_platform" \
    '.platforms[$platform].binary' \
    "$temporary_directory/claude-manifest.json")
if [ "$claude_binary_name" != "claude" ]; then
    echo "unexpected Claude Code binary name: $claude_binary_name" >&2
    exit 1
fi

claude_binary="$temporary_directory/claude"
download "$claude_base_url/$claude_platform/$claude_binary_name" "$claude_binary"
actual_claude_size=$(wc -c < "$claude_binary")
if [ "$actual_claude_size" -ne "$claude_size" ]; then
    echo "Claude Code binary size mismatch: expected $claude_size, got $actual_claude_size" >&2
    exit 1
fi
printf '%s  %s\n' "$claude_checksum" "$claude_binary" | sha256sum -c -

install -d -m 0755 \
    /home/vscode/.local/bin \
    /home/vscode/.local/share/claude/versions
install -m 0755 "$claude_binary" "/home/vscode/.local/share/claude/versions/$claude_version"
ln -sfn "../share/claude/versions/$claude_version" /home/vscode/.local/bin/claude
chown -R vscode:vscode /home/vscode/.local
claude_version_output=$(
    runuser -u vscode -- env DISABLE_AUTOUPDATER=1 DISABLE_UPDATES=1 \
        /home/vscode/.local/bin/claude --version
)
case "$claude_version_output" in
    "$claude_version (Claude Code)") ;;
    *)
        echo "installed Claude Code version does not match $claude_version: $claude_version_output" >&2
        exit 1
        ;;
esac

install -d -m 0755 /usr/local/share/devcontainer
jq \
    --arg aws_installed "$aws_version" \
    --arg claude_installed "$claude_version" \
    '.installed_versions = {
        "aws_cli": $aws_installed,
        "claude_code": $claude_installed
    }' \
    "$temporary_directory/resolved-releases.json" \
    > /usr/local/share/devcontainer/resolved-releases.json
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
    ca-certificates curl git gnupg groff iputils-ping jq less make unzip vim \
    > /usr/local/share/devcontainer/apt-packages.txt
printf '%s\n' "$snapshot_timestamp" \
    > /usr/local/share/devcontainer/apt-snapshot-timestamp.txt

rm -rf /var/lib/apt/lists/*
trap - EXIT HUP INT TERM
cleanup
