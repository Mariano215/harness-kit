#!/usr/bin/env bash
# Downstream condensations of the twelve-primitive model cite the harness-kit
# version they were last reconciled against.
#
# A staleness report, not a sync tool. Nothing here rewrites a consumer: their
# condensations are lossy on purpose and generating them would destroy the fit.
# It reports where a citation has fallen behind contracts.yaml so someone can
# read the diff and decide whether the consumer needs to change.
#
# Exits non-zero naming each consumer whose citation is missing or stale.
# A consumer that is not checked out on this machine is skipped, not failed.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
parent="$(dirname "$root")"
contracts="$root/contracts.yaml"
list="$root/ci/consumers.txt"

version=$(grep -E '^contracts_version:' "$contracts" | tr -d '" ' | cut -d: -f2)
marker="harness-kit contracts $version"

fail=0
checked=0
skipped=0

while IFS= read -r line; do
  case "$line" in
    ''|\#*) continue ;;
  esac
  case "$line" in
    "~"/*) path="$HOME/${line#\~/}" ;;
    /*)    path="$line" ;;
    *)     path="$parent/$line" ;;
  esac
  if [ ! -f "$path" ]; then
    echo "SKIP $line: not checked out here"
    skipped=$((skipped + 1))
    continue
  fi
  checked=$((checked + 1))
  if grep -Fq "$marker" "$path"; then
    continue
  fi
  if grep -Fq "harness-kit contracts" "$path"; then
    stale=$(grep -Fom1 "harness-kit contracts" "$path" >/dev/null && \
            grep -Eom1 'harness-kit contracts [0-9]+\.[0-9]+\.[0-9]+' "$path")
    echo "FAIL $line: cites '$stale', current is contracts $version"
  else
    echo "FAIL $line: no harness-kit citation, expected '$marker'"
  fi
  fail=1
done < "$list"

if [ "$fail" -eq 0 ]; then
  echo "OK $checked consumers cite contracts $version, $skipped skipped"
fi
exit "$fail"
