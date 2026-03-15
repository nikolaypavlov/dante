#!/bin/bash
# Claude Code PreToolUse hook: validate staged JSON before git commit
# Receives tool call JSON on stdin. Exit 0 = allow, exit 2 = block.

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // empty')

# Only trigger on git commit commands
if ! echo "$cmd" | grep -qE '^git commit\b'; then
  exit 0
fi

# Find staged JSON files under json/ (exclude schema)
staged_json=$(git diff --cached --name-only --diff-filter=ACM -- 'json/*.json' \
  | grep -v 'canto\.schema\.json')

# No JSON files staged - nothing to validate
if [ -z "$staged_json" ]; then
  exit 0
fi

# Build argument list of bare filenames
file_args=""
for f in $staged_json; do
  file_args="$file_args $(basename "$f")"
done

# Validate only the staged JSON files
output=$(uv run scripts/validate_json.py $file_args 2>&1)
exit_code=$?

if [ $exit_code -eq 0 ]; then
  exit 0
else
  echo "JSON validation failed for staged files. Fix errors before committing:" >&2
  echo "$output" >&2
  exit 2
fi
