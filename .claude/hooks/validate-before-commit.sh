#!/bin/bash
# Pre-commit hook: validate JSON before allowing git commit
# Exit 0 = allow, exit 2 = block with error message

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // empty')

# Only trigger on git commit commands
if ! echo "$cmd" | grep -q '^git commit'; then
  exit 0
fi

# Run JSON validation
output=$(uv run scripts/validate_json.py 2>&1)
exit_code=$?

if [ $exit_code -eq 0 ]; then
  exit 0
else
  echo "$output" >&2
  exit 2
fi
