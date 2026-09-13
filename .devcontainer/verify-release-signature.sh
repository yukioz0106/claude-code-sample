#!/bin/sh

set -eu

if [ "$#" -ne 5 ]; then
    echo "usage: $0 PUBLIC_KEY GPG_HOME EXPECTED_PRIMARY_FINGERPRINT SIGNATURE PAYLOAD" >&2
    exit 2
fi

public_key=$1
gpg_home=$2
expected_fingerprint=$3
signature=$4
payload=$5

if ! printf '%s\n' "$expected_fingerprint" | grep -Eq '^[A-F0-9]{40}$'; then
    echo "invalid expected signing-key fingerprint: $expected_fingerprint" >&2
    exit 2
fi

# A key endpoint must contain exactly the pinned primary key. In particular,
# checking only the first fingerprint would allow an untrusted second key to be
# imported and used for verification.
if ! primary_fingerprints=$(
    gpg --batch \
        --homedir "$gpg_home" \
        --with-colons \
        --import-options show-only \
        --import "$public_key" 2>/dev/null \
        | awk -F: '
            $1 == "pub" { awaiting_primary_fingerprint = 1; next }
            awaiting_primary_fingerprint && $1 == "fpr" {
                print toupper($10)
                awaiting_primary_fingerprint = 0
            }
        '
); then
    echo "could not inspect release signing key: $public_key" >&2
    exit 1
fi

if [ "$primary_fingerprints" != "$expected_fingerprint" ]; then
    echo "release key file must contain exactly expected primary fingerprint $expected_fingerprint" >&2
    echo "found primary fingerprints: ${primary_fingerprints:-none}" >&2
    exit 1
fi

gpg --batch --homedir "$gpg_home" --import "$public_key"

# Do not trust a successful gpg exit status alone: the keyring may contain
# another valid key. VALIDSIG identifies the key that actually made the valid
# signature; for signing subkeys its final field identifies the primary key.
status_file="$gpg_home/verify-status"
rm -f -- "$status_file"
if ! gpg --batch \
    --homedir "$gpg_home" \
    --status-fd 3 \
    --verify "$signature" "$payload" \
    3>"$status_file"; then
    echo "release signature verification failed: $payload" >&2
    exit 1
fi

if ! awk -v expected="$expected_fingerprint" '
    $1 == "[GNUPG:]" && $2 == "VALIDSIG" {
        signer = toupper($3)
        primary = ($12 == "" ? signer : toupper($12))
        if (primary == expected) {
            signed_by_expected_primary = 1
        }
    }
    END { exit(signed_by_expected_primary ? 0 : 1) }
' "$status_file"; then
    echo "valid release signature was not made by expected primary key $expected_fingerprint" >&2
    exit 1
fi

rm -f -- "$status_file"
