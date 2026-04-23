#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from urllib import error, parse, request

CLAUDE_TEST_PROMPT = "Reply with ok only"
PREFERRED_MODELS = [
    "anthropic/claude-sonnet-4.6",
    "claude-sonnet-4-6",
    "anthropic/claude-sonnet-4.5",
    "claude-sonnet-4-5",
    "anthropic/claude-sonnet-4",
    "claude-sonnet-4",
    "anthropic/claude-3.7-sonnet",
    "claude-3-7-sonnet",
]


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def find_cc_switch() -> Path:
    candidates = [
        shutil.which("cc-switch"),
        str(Path.home() / "AppData" / "Local" / "cc-switch" / "cc-switch.exe"),
        str(Path.home() / "AppData" / "Local" / "Programs" / "CC Switch" / "cc-switch.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise FileNotFoundError("cc-switch.exe not found")


def find_claude() -> str | None:
    return shutil.which("claude")


def normalize_base_url(base_url: str, keep_v1: bool) -> str:
    value = base_url.strip().rstrip("/")
    parsed = parse.urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {base_url}")
    path = parsed.path.rstrip("/")
    if not keep_v1:
        for suffix in ("/v1/messages", "/messages", "/v1"):
            if path.endswith(suffix):
                path = path[: -len(suffix)]
                break
    rebuilt = parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
    return rebuilt.rstrip("/")


def derive_provider_name(name: str | None, base_url: str) -> str:
    if name:
        return name
    host = parse.urlparse(base_url).netloc or "custom-provider"
    return f"CCS {host}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "custom-provider"


def derive_provider_id(base_url: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    parsed = parse.urlparse(base_url)
    host = parsed.netloc or "custom-provider"
    path = parsed.path.strip("/")
    raw = host if not path else f"{host}-{path.replace('/', '-')}"
    return f"ccs-{slugify(raw)}"


def cc_switch_db_path() -> Path:
    return Path.home() / ".cc-switch" / "cc-switch.db"


def backup_db(db_path: Path) -> Path:
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"cc-switch.db.backup.{stamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def run_command(cmd: Sequence[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def fetch_models(base_url: str, api_key: str) -> list[str]:
    url = f"{base_url.rstrip('/')}/v1/models"
    headers_list = [
        {"Authorization": f"Bearer {api_key}"},
        {"x-api-key": api_key},
    ]
    for headers in headers_list:
        req = request.Request(url, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            models = []
            for item in payload.get("data", []):
                model_id = item.get("id") or item.get("api_name")
                if model_id:
                    models.append(model_id)
            if models:
                return models
        except Exception:
            continue
    return []


def direct_messages_test(base_url: str, api_key: str, model: str, prompt: str) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/v1/messages"
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 32,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    header_sets = [
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        {
            "Authorization": f"Bearer {api_key}",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    ]
    for headers in header_sets:
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=40) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            texts = [
                part.get("text", "")
                for part in payload.get("content", [])
                if isinstance(part, dict)
            ]
            return True, " ".join(filter(None, texts)).strip()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return False, f"HTTP {exc.code}: {detail}"
        except Exception as exc:
            last = str(exc)
    return False, last


def preferred_candidate_order(models: list[str], explicit_model: str | None) -> list[str]:
    seen = set()
    ordered: list[str] = []

    def add(model: str | None) -> None:
        if model and model not in seen:
            ordered.append(model)
            seen.add(model)

    add(explicit_model)
    for model in PREFERRED_MODELS:
        if model in models:
            add(model)
    for model in models:
        if "claude-sonnet" in model:
            add(model)
    for model in models:
        if "claude" in model:
            add(model)
    return ordered


def pick_slot_model(models: list[str], primary: str, keyword: str) -> str:
    for model in models:
        if keyword in model:
            return model
    return primary


def build_env(base_url: str, api_key: str, primary_model: str, models: list[str]) -> dict[str, str]:
    return {
        "ANTHROPIC_AUTH_TOKEN": api_key,
        "ANTHROPIC_BASE_URL": base_url,
        "ANTHROPIC_MODEL": primary_model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": pick_slot_model(models, primary_model, "haiku"),
        "ANTHROPIC_DEFAULT_SONNET_MODEL": primary_model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": pick_slot_model(models, primary_model, "opus"),
    }


def upsert_provider(
    db_path: Path,
    provider_id: str,
    provider_name: str,
    base_url: str,
    env_map: dict[str, str],
) -> None:
    meta = json.dumps(
        {"commonConfigEnabled": True, "endpointAutoSelect": True, "apiFormat": "anthropic"},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    settings = json.dumps({"env": env_map}, ensure_ascii=False, separators=(",", ":"))
    now_ms = int(time.time() * 1000)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute(
        "DELETE FROM provider_health WHERE provider_id=? AND app_type='claude'",
        (provider_id,),
    )
    cur.execute(
        "DELETE FROM provider_endpoints WHERE provider_id=? AND app_type='claude'",
        (provider_id,),
    )
    cur.execute("DELETE FROM providers WHERE id=? AND app_type='claude'", (provider_id,))
    cur.execute(
        """
        INSERT INTO providers
        (id, app_type, name, settings_config, website_url, category, created_at, sort_index, notes,
         icon, icon_color, meta, is_current, in_failover_queue, cost_multiplier, limit_daily_usd,
         limit_monthly_usd, provider_type)
        VALUES (
            ?, 'claude', ?, ?, NULL, 'custom', ?, NULL, NULL, NULL, NULL, ?,
            0, 0, '1.0', NULL, NULL, NULL
        )
        """,
        (provider_id, provider_name, settings, now_ms, meta),
    )
    cur.execute(
        """
        INSERT INTO provider_endpoints (provider_id, app_type, url, added_at)
        VALUES (?, 'claude', ?, ?)
        """,
        (provider_id, base_url, now_ms),
    )
    cur.execute(
        """
        INSERT INTO provider_health
        (
            provider_id, app_type, is_healthy, consecutive_failures,
            last_success_at, last_failure_at, last_error, updated_at
        )
        VALUES (?, 'claude', 1, 0, NULL, NULL, NULL, datetime('now'))
        """,
        (provider_id,),
    )
    conn.commit()
    conn.close()


def write_claude_settings(env_map: dict[str, str]) -> Path:
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    data: dict[str, object] = {"includeCoAuthoredBy": False}
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            data = {"includeCoAuthoredBy": False}
    data["env"] = env_map
    if "includeCoAuthoredBy" not in data:
        data["includeCoAuthoredBy"] = False
    settings_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return settings_path


def switch_provider(cc_switch: Path, provider_id: str) -> subprocess.CompletedProcess[str]:
    return run_command([str(cc_switch), "-a", "claude", "provider", "switch", provider_id])


def claude_smoke_test(prompt: str, timeout: int = 45) -> tuple[bool, str]:
    claude = find_claude()
    if not claude:
        return False, "claude command not found"
    result = run_command([claude, prompt], timeout=timeout)
    combined = "\n".join(
        part for part in (result.stdout.strip(), result.stderr.strip()) if part
    ).strip()
    return result.returncode == 0, combined or "(no output)"


def should_try_next_model(message: str) -> bool:
    lower = message.lower()
    return (
        "model_not_allowed" in lower
        or "selected model" in lower
        or "does not support this model" in lower
        or "may not exist or you may not have access" in lower
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure Claude Code via CC Switch with a third-party provider."
    )
    parser.add_argument("--base-url", required=True, help="Claude-compatible base URL")
    parser.add_argument("--api-key", required=True, help="API key for the provider")
    parser.add_argument("--name", help="Provider display name in CC Switch")
    parser.add_argument("--provider-id", help="Stable provider id in CC Switch")
    parser.add_argument("--model", help="Preferred primary model id")
    parser.add_argument(
        "--keep-v1", action="store_true", help="Keep a trailing /v1 in the stored base URL"
    )
    parser.add_argument(
        "--skip-claude-test", action="store_true", help="Skip live claude smoke test"
    )
    parser.add_argument(
        "--test-prompt", default=CLAUDE_TEST_PROMPT, help="Prompt used for claude smoke test"
    )
    args = parser.parse_args()

    cc_switch = find_cc_switch()
    db_path = cc_switch_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"CC Switch database not found: {db_path}")

    normalized_url = normalize_base_url(args.base_url, args.keep_v1)
    provider_name = derive_provider_name(args.name, normalized_url)
    provider_id = derive_provider_id(normalized_url, args.provider_id)
    backup_path = backup_db(db_path)
    models = fetch_models(normalized_url, args.api_key)
    candidates = preferred_candidate_order(models, args.model)
    if not candidates:
        candidates = [args.model] if args.model else PREFERRED_MODELS[:]

    last_message = ""
    chosen_env: dict[str, str] | None = None

    for candidate in candidates:
        env_map = build_env(normalized_url, args.api_key, candidate, models)
        upsert_provider(db_path, provider_id, provider_name, normalized_url, env_map)
        switched = switch_provider(cc_switch, provider_id)
        if switched.returncode != 0:
            eprint(switched.stderr.strip() or switched.stdout.strip())
            return 1
        write_claude_settings(env_map)

        if args.skip_claude_test:
            chosen_env = env_map
            last_message = "Skipped claude smoke test by request."
            break

        ok, message = claude_smoke_test(args.test_prompt)
        last_message = message
        if ok:
            chosen_env = env_map
            break
        if not should_try_next_model(message):
            # Fallback to direct API test for clearer diagnostics.
            direct_ok, direct_message = direct_messages_test(
                normalized_url, args.api_key, candidate, args.test_prompt
            )
            last_message = f"{message}\nDirect API test: {direct_message}"
            if direct_ok:
                chosen_env = env_map
            break

    if not chosen_env:
        print(
            json.dumps(
                {
                    "ok": False,
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "base_url": normalized_url,
                    "backup_db": str(backup_path),
                    "tested_models": candidates,
                    "message": last_message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "provider_id": provider_id,
                "provider_name": provider_name,
                "base_url": normalized_url,
                "backup_db": str(backup_path),
                "primary_model": chosen_env["ANTHROPIC_MODEL"],
                "haiku_model": chosen_env["ANTHROPIC_DEFAULT_HAIKU_MODEL"],
                "sonnet_model": chosen_env["ANTHROPIC_DEFAULT_SONNET_MODEL"],
                "opus_model": chosen_env["ANTHROPIC_DEFAULT_OPUS_MODEL"],
                "available_models_count": len(models),
                "message": last_message,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
