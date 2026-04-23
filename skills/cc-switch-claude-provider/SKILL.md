---
name: cc-switch-claude-provider
description: Configure Claude Code through local CC Switch with a third-party Anthropic or Claude-compatible base URL and API key. Use when the user wants "just give base URL + key and make Claude Code usable", wants to switch Claude Code to a third-party provider without manual editing, or wants CC Switch provider creation, provider switching, and a real Claude Code smoke test automated.
---

# CC Switch Claude Provider

Use this skill to wire a third-party Claude-compatible endpoint into local `CC Switch`, activate it for Claude Code, and verify that `claude` can actually answer.

## Quick Start

Run the setup script from this skill directory with the user-provided `base URL` and `API key`:

```powershell
python ".\scripts\configure_cc_switch_claude_provider.py" --base-url "<BASE_URL>" --api-key "<API_KEY>"
```

Use these optional flags when needed:

```powershell
python ".\scripts\configure_cc_switch_claude_provider.py" `
  --base-url "<BASE_URL>" `
  --api-key "<API_KEY>" `
  --name "<PROVIDER_NAME>" `
  --model "<MODEL_ID>" `
  --keep-v1
```

## Workflow

1. Collect the user's `base URL` and `API key`.
2. Run the script.
3. Read the result summary:
   - `provider_id`
   - normalized `base_url`
   - chosen models
   - whether `claude` smoke test passed
4. If the script reports success, tell the user Claude Code is ready.
5. If the script reports failure, relay the concrete error and next fallback it already attempted.

## What The Script Does

- Find local `cc-switch.exe` and `claude`
- Back up `<HOME>\.cc-switch\cc-switch.db`
- Normalize Claude-style endpoints; by default it strips a trailing `/v1`
- Query `/v1/models` when available
- Create or update a Claude provider in CC Switch
- Switch the current Claude provider to the new entry
- Sync `<HOME>\.claude\settings.json`
- Run a real `claude "Reply with ok only"` smoke test
- Auto-fallback across likely Claude model IDs if the first model is rejected

## Default Behavior

- Default provider name: derived from the endpoint host
- Default provider id: stable slug derived from host
- Default model preference order:
  1. `anthropic/claude-sonnet-4.6`
  2. `claude-sonnet-4-6`
  3. `anthropic/claude-sonnet-4.5`
  4. `anthropic/claude-sonnet-4`
  5. `anthropic/claude-3.7-sonnet`
- Default smoke-test prompt: `Reply with ok only`

## When To Override Defaults

- Pass `--keep-v1` if the user explicitly says the full endpoint must keep `/v1`
- Pass `--model` if the provider only allows a specific model
- Pass `--name` if the user wants a friendly provider label in CC Switch
- Pass `--skip-claude-test` only when the user explicitly does not want a live test

## Output Handling

On success, summarize:

- the active provider name
- the active base URL
- the selected primary model
- the smoke-test response

On failure, summarize:

- whether CC Switch write succeeded
- whether provider switch succeeded
- whether direct API probing succeeded
- the exact failing step

## Script

- Main automation: [scripts/configure_cc_switch_claude_provider.py](./scripts/configure_cc_switch_claude_provider.py)
