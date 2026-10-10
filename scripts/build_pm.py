#!/usr/bin/env python3
"""PM 보드 HTML 생성.

PM/pm_data.json(할 일·재고·주기·계기판의 유일한 원본)을 PM/board_template.html에 끼워서
PM/PM_보드.html을 만듦. 보드를 고칠 땐 JSON만 고치고 이 스크립트를 다시 돌림.

사용법:
    python3 scripts/build_pm.py

종료 코드: JSON 형식이나 필수 키가 틀리면 1.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "PM" / "pm_data.json"
TEMPLATE = ROOT / "PM" / "board_template.html"
OUT = ROOT / "PM" / "PM_보드.html"

REQUIRED = ["updated", "next_pm", "principle", "goal", "model", "samboo", "routes", "milestones",
            "income", "trends", "stamina", "backlog", "hours", "week", "month", "gauges",
            "inventory_note", "inventory", "weekgrid", "cadence", "proposals", "axes",
            "sources", "conflicts", "log"]
AXES = {"purpleant", "foorog", "career", "side", "asset", "health", "pm"}


def check(data):
    errors = [f"필수 키 없음: {k}" for k in REQUIRED if k not in data]
    ids = []
    for part in ("week", "month"):
        for t in data.get(part, {}).get("tasks", []):
            ids.append(t.get("id"))
            if t.get("axis") not in AXES:
                errors.append(f"{t.get('id')}: 모르는 축 '{t.get('axis')}'")
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"할 일 id 중복: {', '.join(sorted(dup))} — 체크 상태가 섞임")
    if len(data.get("week", {}).get("tasks", [])) > 8:
        errors.append("이번 주 할 일이 8개를 넘음 — 전선 줄이기 원칙 위반")
    return errors


def main():
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[FAIL] {DATA.name} JSON 오류 — {e}")
        return 1
    errors = check(data)
    for e in errors:
        print(f"[FAIL] {e}")
    if errors:
        return 1
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*PM_DATA*/", blob, 1)
    OUT.write_text(html, encoding="utf-8")
    week = data["week"]
    print(f"[PASS] {OUT.relative_to(ROOT)} — {week['id']} 할 일 {len(week['tasks'])}개 · "
          f"이번 달 {len(data['month']['tasks'])}개 · 재고 {len(data['inventory'])}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
