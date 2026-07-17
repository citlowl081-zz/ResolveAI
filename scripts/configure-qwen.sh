#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
EXAMPLE_FILE="${ROOT_DIR}/.env.example"

if [[ ! -f "${EXAMPLE_FILE}" ]]; then
  echo "ERROR: .env.example not found; run this script from the ResolveAI repository."
  exit 1
fi

umask 077
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${EXAMPLE_FILE}" "${ENV_FILE}"
fi
chmod 600 "${ENV_FILE}"

read -r -s -p "Enter a NEW Bailian API Key (input hidden): " NEW_KEY
echo
if [[ -z "${NEW_KEY}" ]]; then
  echo "ERROR: API Key cannot be empty."
  unset NEW_KEY
  exit 1
fi

read -r -p "Enter the Bailian OpenAI-compatible Base URL: " BASE_URL
if [[ -z "${BASE_URL}" ]]; then
  echo "ERROR: Base URL cannot be empty."
  unset NEW_KEY BASE_URL
  exit 1
fi
if [[ "${BASE_URL}" != https://*/compatible-mode/v1 ]]; then
  echo "ERROR: Base URL must use HTTPS and end with /compatible-mode/v1."
  unset NEW_KEY BASE_URL
  exit 1
fi

read -r -p "Model [qwen3.7-plus]: " MODEL
MODEL="${MODEL:-qwen3.7-plus}"

TMP_FILE="$(mktemp "${ROOT_DIR}/.env.tmp.XXXXXX")"
chmod 600 "${TMP_FILE}"
trap 'rm -f "${TMP_FILE:-}"; unset NEW_KEY BASE_URL MODEL entry key value' EXIT

update_env_value() {
  local key="$1"
  local value="$2"
  local source_file="$3"
  local destination_file="$4"
  local found=0
  : > "${destination_file}"
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" == "${key}="* ]]; then
      printf '%s=%s\n' "${key}" "${value}" >> "${destination_file}"
      found=1
    else
      printf '%s\n' "${line}" >> "${destination_file}"
    fi
  done < "${source_file}"
  if [[ "${found}" -eq 0 ]]; then
    printf '%s=%s\n' "${key}" "${value}" >> "${destination_file}"
  fi
}

for entry in \
  "LLM_PROVIDER=openai_compatible" \
  "LLM_MODEL=${MODEL}" \
  "LLM_API_KEY=${NEW_KEY}" \
  "LLM_BASE_URL=${BASE_URL}" \
  "EMBEDDING_PROVIDER=mock"
do
  key="${entry%%=*}"
  value="${entry#*=}"
  update_env_value "${key}" "${value}" "${ENV_FILE}" "${TMP_FILE}"
  mv "${TMP_FILE}" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  TMP_FILE="$(mktemp "${ROOT_DIR}/.env.tmp.XXXXXX")"
  chmod 600 "${TMP_FILE}"
done

scheme="${BASE_URL%%://*}"
remainder="${BASE_URL#*://}"
host="${remainder%%/*}"
host_prefix="${host%%.*}"
host_suffix="${host#*.}"
masked_prefix="${host_prefix:0:3}****"

echo "Qwen local configuration updated."
echo "Provider: openai_compatible"
echo "Model: ${MODEL}"
echo "Base URL: ${scheme}://${masked_prefix}.${host_suffix}/compatible-mode/v1"
echo "Embedding provider: mock"
echo "Security: .env permissions set to 600; do not run 'git add .env'."

unset NEW_KEY BASE_URL MODEL entry key value
