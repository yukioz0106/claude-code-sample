#!/usr/bin/env bash
set -euo pipefail

umask 077

OPS_PROFILE="${OPS_PROFILE:-bedrock}"
LOGIN_PROFILE="${LOGIN_PROFILE:-${OPS_PROFILE}-login}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"
EXPECTED_AWS_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-013958956098}"
AWS_CONFIG_FILE_PATH="${AWS_CONFIG_FILE:-${HOME}/.aws/config}"
AWS_CREDENTIALS_FILE_PATH="${AWS_SHARED_CREDENTIALS_FILE:-${HOME}/.aws/credentials}"
MINIMUM_AWS_CLI_VERSION="2.32.0"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

validate_profile_name() {
    local profile_name="$1"

    [[ "${profile_name}" =~ ^[A-Za-z0-9_.-]+$ ]] ||
        fail "AWS profile names may contain only letters, numbers, dots, underscores, and hyphens: ${profile_name}"
}

remove_ini_section() {
    local file_path="$1"
    local section_name="$2"
    local tmp_file

    if [[ ! -f "${file_path}" ]]; then
        return 0
    fi

    tmp_file="$(mktemp)"
    awk -v section="[${section_name}]" '
        $0 == section {
            skip = 1
            next
        }
        /^\[/ {
            skip = 0
        }
        !skip {
            print
        }
    ' "${file_path}" > "${tmp_file}"
    mv "${tmp_file}" "${file_path}"
    chmod 600 "${file_path}"
}

validate_profile_name "${OPS_PROFILE}"
validate_profile_name "${LOGIN_PROFILE}"
[[ "${OPS_PROFILE}" != "${LOGIN_PROFILE}" ]] ||
    fail "OPS_PROFILE and LOGIN_PROFILE must be different."
[[ "${AWS_REGION}" =~ ^[a-z0-9-]+$ ]] ||
    fail "AWS_REGION contains unsupported characters: ${AWS_REGION}"
[[ "${EXPECTED_AWS_ACCOUNT_ID}" =~ ^[0-9]{12}$ ]] ||
    fail "EXPECTED_AWS_ACCOUNT_ID must be a 12-digit AWS account ID."

command -v aws >/dev/null 2>&1 || fail "AWS CLI was not found."

aws_cli_version_output="$(aws --version 2>&1)"
aws_cli_version="${aws_cli_version_output#aws-cli/}"
aws_cli_version="${aws_cli_version%% *}"
[[ "${aws_cli_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
    fail "Could not determine the AWS CLI version: ${aws_cli_version_output}"

oldest_version="$(printf '%s\n%s\n' "${MINIMUM_AWS_CLI_VERSION}" "${aws_cli_version}" | sort -V | head -n 1)"
[[ "${oldest_version}" == "${MINIMUM_AWS_CLI_VERSION}" ]] ||
    fail "aws login requires AWS CLI ${MINIMUM_AWS_CLI_VERSION} or later (found ${aws_cli_version})."

mkdir -p "$(dirname "${AWS_CONFIG_FILE_PATH}")" "$(dirname "${AWS_CREDENTIALS_FILE_PATH}")"
chmod 700 "${HOME}/.aws"

login_args=(login --profile "${LOGIN_PROFILE}" --region "${AWS_REGION}")
case "${AWS_LOGIN_REMOTE:-1}" in
    1)
        login_args+=(--remote)
        ;;
    0)
        ;;
    *)
        fail "AWS_LOGIN_REMOTE must be 1 (cross-device) or 0 (same-device)."
        ;;
esac

printf 'Logging in to AWS profile [%s] in region [%s]...\n' "${LOGIN_PROFILE}" "${AWS_REGION}"
aws "${login_args[@]}"

identity="$(aws sts get-caller-identity \
    --profile "${LOGIN_PROFILE}" \
    --query '[Account,Arn,UserId]' \
    --output text)"
IFS=$'\t' read -r actual_account_id actual_arn actual_user_id <<< "${identity}"

if [[ "${actual_account_id}" != "${EXPECTED_AWS_ACCOUNT_ID}" ]]; then
    aws logout --profile "${LOGIN_PROFILE}" >/dev/null 2>&1 || true
    fail "Unexpected AWS account. expected=${EXPECTED_AWS_ACCOUNT_ID} actual=${actual_account_id} arn=${actual_arn}"
fi

printf 'Verified AWS identity: account=%s arn=%s userId=%s\n' \
    "${actual_account_id}" "${actual_arn}" "${actual_user_id}"

# Static credentials take precedence over login credentials. Remove only the
# operational profile from this Dev Container's isolated AWS storage, then
# expose the login profile through credential_process for Claude Code and SDKs.
remove_ini_section "${AWS_CREDENTIALS_FILE_PATH}" "${OPS_PROFILE}"
# AWS config uses [default] for the default profile and [profile name] for named profiles.
if [[ "${OPS_PROFILE}" == "default" ]]; then
    remove_ini_section "${AWS_CONFIG_FILE_PATH}" "default"
else
    remove_ini_section "${AWS_CONFIG_FILE_PATH}" "profile ${OPS_PROFILE}"
fi

aws configure set region "${AWS_REGION}" --profile "${LOGIN_PROFILE}"
aws configure set region "${AWS_REGION}" --profile "${OPS_PROFILE}"
aws configure set output json --profile "${OPS_PROFILE}"
aws configure set credential_process \
    "aws configure export-credentials --profile ${LOGIN_PROFILE} --format process" \
    --profile "${OPS_PROFILE}"

printf '%s\n' "--- Verified identity (${OPS_PROFILE}) ---"
aws sts get-caller-identity --profile "${OPS_PROFILE}" --output table
printf 'AWS login succeeded. Claude Code will use profile [%s].\n' "${OPS_PROFILE}"
