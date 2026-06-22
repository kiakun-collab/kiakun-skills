#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


FULL_FIELDS = [
    "玩家当前阶段",
    "玩家目标",
    "入口",
    "第一眼信息",
    "主操作",
    "可选操作",
    "成功反馈",
    "阻断原因",
    "恢复路径",
    "下一步",
    "不展示信息",
    "证据层级",
    "not_proven",
]

SHORT_FIELDS = [
    "玩家目标",
    "入口",
    "主操作",
    "成功反馈",
    "阻断原因",
    "恢复路径",
    "不展示信息",
    "证据层级",
    "not_proven",
]

FULL_ONLY_FIELDS = set(FULL_FIELDS) - set(SHORT_FIELDS)
ALLOWED_LAYERS = [
    "logic_runner",
    "ui_contract",
    "interactive_mcp",
    "visible_capture",
    "manual_canary",
    "natural UI-only",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate player interaction contract fields in markdown files."
    )
    parser.add_argument(
        "--mode",
        choices=["full", "short", "auto"],
        default="auto",
        help="Contract field set to validate.",
    )
    parser.add_argument("files", nargs="+", help="Markdown files to validate.")
    return parser.parse_args()


def field_pattern(field):
    return re.compile(
        rf"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(field)}(?:\*\*)?\s*[：:]\s*(.+?)\s*$"
    )


def find_field_value(text, field):
    values = find_field_values(text, field)
    if not values:
        return None
    return values[0]


def find_field_values(text, field):
    values = []
    for match in field_pattern(field).finditer(text):
        value = match.group(1).strip()
        if value:
            values.append(value)
    return values


def mode_fields(mode, text):
    if mode == "full":
        return FULL_FIELDS
    if mode == "short":
        return SHORT_FIELDS
    if "玩家互动合同（完整）" in text:
        return FULL_FIELDS
    if "玩家互动合同（短）" in text:
        return SHORT_FIELDS
    for field in FULL_ONLY_FIELDS:
        if find_field_value(text, field):
            return FULL_FIELDS
    return SHORT_FIELDS


def validate_fields(text, fields):
    errors = []
    for field in fields:
        if not find_field_value(text, field):
            errors.append(f"missing_or_empty_field:{field}")
    return errors


def validate_evidence_layers(text):
    errors = []
    evidence_values = find_field_values(text, "证据层级")
    if not evidence_values:
        return ["missing_or_empty_field:证据层级"]

    for value in evidence_values:
        masked = value
        found = False
        for layer in ALLOWED_LAYERS:
            if layer in value:
                found = True
                masked = masked.replace(layer, " ")
        masked_clean = re.sub(r"（[^）]*）|\([^)]*\)", "", masked)
        ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", masked_clean)
        if ascii_tokens:
            errors.append(
                "invalid_evidence_layer:"
                + ",".join(sorted(set(ascii_tokens)))
                + f" in {value}"
            )
        if not found:
            errors.append(f"missing_allowed_evidence_layer:{value}")
    return errors


def validate_natural_ui_only_guard(text):
    natural_evidence_values = [
        value for value in find_field_values(text, "证据层级") if "natural UI-only" in value
    ]
    if not natural_evidence_values:
        return []
    guard_text = "\n".join(
        natural_evidence_values
        + find_field_values(text, "证据说明")
        + find_field_values(text, "not_proven")
    )
    required = [
        "任务明确要求",
        "无 fixture",
        "无 direct manager/API",
        "无加速",
        "无桥接支撑",
    ]
    missing = [item for item in required if item not in guard_text]
    if not missing:
        return []
    return ["natural_ui_only_missing_guard:" + ",".join(missing)]


def validate_file(path, mode):
    text = Path(path).read_text(encoding="utf-8")
    fields = mode_fields(mode, text)
    errors = []
    errors.extend(validate_fields(text, fields))
    errors.extend(validate_evidence_layers(text))
    errors.extend(validate_natural_ui_only_guard(text))
    return errors


def main():
    args = parse_args()
    failed = False
    for raw_path in args.files:
        path = Path(raw_path)
        if not path.is_file():
            print(f"PLAYER_INTERACTION_CONTRACT_VALIDATION: FAIL {raw_path}: file_not_found")
            failed = True
            continue
        errors = validate_file(path, args.mode)
        if errors:
            failed = True
            print(f"PLAYER_INTERACTION_CONTRACT_VALIDATION: FAIL {raw_path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PLAYER_INTERACTION_CONTRACT_VALIDATION: PASS {raw_path}")

    if failed:
        print("PLAYER_INTERACTION_CONTRACT_VALIDATION_RESULT: FAIL")
        return 1
    print("PLAYER_INTERACTION_CONTRACT_VALIDATION_RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
