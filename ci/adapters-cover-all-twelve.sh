#!/usr/bin/env bash
# Every standalone adapter states all twelve primitives and carries the version
# footer.
#
# This is what replaces a generator. Adapters are hand-written because a
# CLAUDE.md, a vendor-neutral AGENTS.md and a pasteable chat brief are three
# different rhetorics. The failure that actually happens is revising one
# primitive in contracts.yaml and leaving one adapter behind, and this catches
# exactly that.
#
# Exits non-zero naming the adapter and the primitive it is missing.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
contracts="$root/contracts.yaml"

adapters=(
  "adapters/agents/AGENTS.md"
  "adapters/claude/CLAUDE.md"
  "adapters/plain-prompt/brief.md"
)

keys=$(grep -E '^  - key: ' "$contracts" | sed 's/^  - key: //')
count=$(printf '%s\n' "$keys" | grep -c .)
if [ "$count" -ne 12 ]; then
  echo "FAIL contracts.yaml: expected 12 primitives, found $count"
  exit 1
fi

version=$(grep -E '^contracts_version:' "$contracts" | tr -d '" ' | cut -d: -f2)
spec=$(grep -E '^spec_version:' "$contracts" | tr -d '" ' | cut -d: -f2)
footer="harness-kit contracts $version"

fail=0
for adapter in "${adapters[@]}"; do
  path="$root/$adapter"
  if [ ! -f "$path" ]; then
    echo "FAIL $adapter: missing"
    fail=1
    continue
  fi
  while IFS= read -r key; do
    # A key is written in prose with a space or a hyphen where the yaml has an
    # underscore: sub_agents appears as "Sub-agents".
    pattern=$(printf '%s' "$key" | sed 's/_/[ _-]/g')
    if ! grep -Eiq "$pattern" "$path"; then
      echo "FAIL $adapter: does not state primitive '$key'"
      fail=1
    fi
  done <<< "$keys"
  if ! grep -Fq "$footer" "$path"; then
    echo "FAIL $adapter: missing or stale footer, expected '$footer'"
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "OK ${#adapters[@]} adapters state all 12 primitives at contracts $version, spec $spec"
fi
exit "$fail"
