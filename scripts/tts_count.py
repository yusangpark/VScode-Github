#!/usr/bin/env python3
"""푸로그 유튜브 숏폼 낭독 대본(v11) 분량·형식 검사.

foorog-content 스킬 v11 규칙을 기계적으로 검증함:
  - 공백 제외 글자수 → 1.0배속 예상 길이 (한국어 TTS ≈ 5.5자/초)
  - 목표 길이별 글자수·문장수 구간
  - 한 문장 15~30자 (40자 초과는 잘라야 함)
  - TTS가 못 읽는 문자(이모지·해시태그·별표·원문자·괄호주석 등)

사용법:
    python3 scripts/tts_count.py 대본.txt
    python3 scripts/tts_count.py 대본.txt --target 40
    pbpaste | python3 scripts/tts_count.py -
"""

import argparse
import re
import sys

CPS = 5.5  # 한국어 TTS 1.0배속 초당 글자수 (공백 제외)

# 목표길이: (글자수 min, max, 문장수 min, max)
TARGETS = {
    30: (150, 170, 6, 7),
    35: (175, 200, 7, 8),
    40: (200, 225, 8, 9),
}

FORBIDDEN = [
    (re.compile(r"#\S+"), "해시태그"),
    (re.compile(r"\*\*"), "굵게(**)"),
    (re.compile(r"[①-⑳]"), "원문자(①②③)"),
    (re.compile(r"[☀-➿\U0001f300-\U0001faff⬀-⯿️]"), "이모지"),
    (re.compile(r"\([^)]*\)"), "괄호주석"),
    (re.compile(r"\S+/\S+"), "슬래시 나열"),
]


def sentences(text):
    """한 문장 = 한 줄 규칙이라 빈 줄이 아닌 줄을 문장으로 셈."""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("path", help="대본 파일 경로 ('-'는 표준입력)")
    ap.add_argument("--target", type=int, default=35, choices=sorted(TARGETS),
                    help="목표 길이(초). 기본 35")
    args = ap.parse_args()

    text = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()

    lines = sentences(text)
    n_chars = len(re.sub(r"\s", "", text))
    secs = n_chars / CPS
    lo_c, hi_c, lo_s, hi_s = TARGETS[args.target]

    print(f"=== 푸로그 숏폼 대본 검사 (목표 {args.target}초) ===\n")
    print(f"공백 제외 글자수 : {n_chars}자  (기준 {lo_c}~{hi_c}자)")
    print(f"1.0배속 예상     : 약 {secs:.1f}초")
    print(f"문장 수          : {len(lines)}문장  (기준 {lo_s}~{hi_s}문장)\n")

    fails = 0

    if lo_c <= n_chars <= hi_c:
        print("[PASS] 글자수 구간")
    else:
        fails += 1
        diff = n_chars - (hi_c if n_chars > hi_c else lo_c)
        print(f"[FAIL] 글자수 구간 — {abs(diff)}자 {'초과' if diff > 0 else '부족'}")

    if lo_s <= len(lines) <= hi_s:
        print("[PASS] 문장 수 구간")
    else:
        fails += 1
        print(f"[FAIL] 문장 수 구간 — {len(lines)}문장")

    # 문장별 길이 (공백 제외 15~30자, 40자 초과는 반드시 자름)
    long_lines = []
    for i, ln in enumerate(lines, 1):
        c = len(re.sub(r"\s", "", ln))
        if c > 40:
            long_lines.append((i, c, ln, True))
        elif c > 30 or c < 15:
            long_lines.append((i, c, ln, False))
    if not long_lines:
        print("[PASS] 문장별 길이 15~30자")
    else:
        hard = [x for x in long_lines if x[3]]
        if hard:
            fails += 1
        print(f"[{'FAIL' if hard else 'WARN'}] 문장별 길이 15~30자")
        for i, c, ln, is_hard in long_lines:
            tag = "40자 초과 — 잘라야 함" if is_hard else "구간 밖"
            print(f"        {i}번({c}자, {tag}): {ln[:34]}")

    # TTS 미독해 문자
    found = []
    for pat, name in FORBIDDEN:
        m = pat.findall(text)
        if m:
            found.append(f"{name} {len(m)}건")
    if found:
        fails += 1
        print(f"[FAIL] TTS 미독해 문자 — {', '.join(found)}")
    else:
        print("[PASS] TTS 미독해 문자 없음")

    # 첫 줄 훅 — 도입 예고형 금지
    if lines and re.search(r"(오늘 소개할|오늘은|소개해\s*드릴|알아보)", lines[0]):
        fails += 1
        print(f"[FAIL] 첫 줄 훅 — 도입 예고형: {lines[0][:30]}")
    else:
        print("[PASS] 첫 줄 도입 예고형 아님")

    print(f"\n실패 {fails}건")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
