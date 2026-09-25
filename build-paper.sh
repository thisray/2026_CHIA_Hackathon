#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
output_root="${1:-"$repo_root/../chia-v8-paper-build"}"

if ! command -v tectonic >/dev/null 2>&1; then
  printf 'tectonic is required to rebuild the documents.\n' >&2
  exit 1
fi

mkdir -p "$output_root"
output_root="$(cd "$output_root" && pwd -P)"
case "$output_root" in
  "$repo_root"|"$repo_root"/*)
    printf 'Choose an output directory outside the repository.\n' >&2
    exit 1
    ;;
esac

mkdir -p "$output_root/paper" "$output_root/supplement"
(cd "$repo_root/paper" && tectonic --outdir "$output_root/paper" CHIA_ECC_Feedback.tex)
(cd "$repo_root/supplement" && tectonic --outdir "$output_root/supplement" Expanded_Evidence.tex)

printf 'Built PDFs in %s\n' "$output_root"
