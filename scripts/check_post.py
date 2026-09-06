#!/usr/bin/env python3
"""퍼플앤트 HTML 포스팅 셀프체크 자동화.

purple-ant-blog-post 스킬 3단계 셀프체크 중 '기계가 대신 셀 수 있는 항목'만 검사함.
팩트 교차확인·프레이밍처럼 사람이 판단할 항목은 여기서 다루지 않음.

사용법:
    python3 scripts/check_post.py "퍼플앤트 블로그/20260906_여의도.html"

종료 코드: FAIL이 하나라도 있으면 1, 아니면 0.
"""

import re
import sys
from pathlib import Path

# .quote 안의 관계자 인용문은 존댓말이 정상이라 말투 검사에서 제외함
QUOTE_BLOCK = re.compile(r'<[^>]*class="[^"]*\bquote\b[^"]*"[^>]*>.*?</[^>]+>', re.S | re.I)
TAG = re.compile(r"<[^>]+>")
STYLE_BLOCK = re.compile(r"<style\b.*?</style>", re.S | re.I)

JONDAETMAL = ["습니다", "해요", "예요", "네요", "세요", "이에요"]
CLICHE_TRANSITIONS = ["무엇보다", "특히", "한편", "결론적으로"]
FLAT_ENDINGS = ["귀추가 주목", "지켜봐야", "주목된다", "주목됨"]
HYPE = ["무조건", "지금이 기회", "확실히 오름", "반드시 오"]

DARK_HEX = re.compile(r"background[^;:]*:\s*[^;]*#([0-3][0-9a-f]{5}|[0-3][0-9a-f]{2})\b", re.I)
LIGHT_TEXT = re.compile(r"color\s*:\s*(#f[0-9a-f]{2,5}|#e[0-9a-f]{2,5}|white)\b", re.I)


class Report:
    def __init__(self):
        self.rows = []

    def add(self, ok, label, detail="", warn=False):
        self.rows.append((ok, warn, label, detail))

    def render(self):
        failed = 0
        for ok, warn, label, detail in self.rows:
            if ok:
                mark = "PASS"
            elif warn:
                mark = "WARN"
            else:
                mark = "FAIL"
                failed += 1
            line = f"[{mark}] {label}"
            if detail:
                line += f" — {detail}"
            print(line)
        print()
        print(f"검사 {len(self.rows)}건 / 실패 {failed}건")
        return failed


def visible_text(html):
    """말투 검사용 본문.

    제외 대상:
      - <style> 블록
      - .quote 관계자 인용문 (원문이 존댓말인 게 정상)
      - "안녕하세요 퍼플앤트임" (스킬이 의무화한 고정 브랜드 인사)
    """
    stripped = STYLE_BLOCK.sub(" ", html)
    stripped = QUOTE_BLOCK.sub(" ", stripped)
    stripped = TAG.sub(" ", stripped)
    return stripped.replace("안녕하세요", " ")


def hits(text, needles):
    return [n for n in needles if n in text]


def check(path):
    html = Path(path).read_text(encoding="utf-8")
    body = visible_text(html)
    rep = Report()

    # 1. 음슴체 — 존댓말 종결 0건 (인용문 제외)
    found = hits(body, JONDAETMAL)
    rep.add(not found, "음슴체 유지 (존댓말 종결 0건)",
            f"검출: {', '.join(found)}" if found else "인용문(.quote) 제외 기준")

    # 2. AI티 — 상투 전환어
    found = hits(body, CLICHE_TRANSITIONS)
    rep.add(not found, "상투 전환어 없음", f"검출: {', '.join(found)}" if found else "", warn=True)

    # 3. AI티 — 뻔한 마무리
    found = hits(body, FLAT_ENDINGS)
    rep.add(not found, "뻔한 마무리 없음", f"검출: {', '.join(found)}" if found else "")

    # 4. 단정적 투자 어조
    found = hits(body, HYPE)
    rep.add(not found, "단정적 투자 어조 없음", f"검출: {', '.join(found)}" if found else "")

    # 5. .verdict 최대 1개 (말미 전용)
    n_verdict = len(re.findall(r'class="[^"]*\bverdict\b', html))
    rep.add(n_verdict <= 1, ".verdict 최대 1개", f"현재 {n_verdict}개")

    # 6. imgbox 사진 번호 유일 + 1부터 연속
    nums = [int(n) for n in re.findall(r"사진\s*(\d+)\s*삽입", html)]
    if not nums:
        rep.add(False, "imgbox 사진 슬롯 존재", "사진N 삽입 슬롯이 하나도 없음")
    else:
        dup = sorted({n for n in nums if nums.count(n) > 1})
        seq_ok = sorted(nums) == list(range(1, len(nums) + 1))
        rep.add(not dup, "사진 번호 중복 없음", f"중복: {dup}" if dup else f"{len(nums)}개")
        rep.add(seq_ok, "사진 번호 1부터 연속", f"현재: {sorted(nums)}" if not seq_ok else "")

    # 7. 하단 출처 블록
    rep.add(bool(re.search(r'class="[^"]*\bsrc\b', html)), "하단 .src 출처 블록 존재")

    # 8. 브랜드 인트로
    rep.add("퍼플앤트임" in body, "인트로 브랜드 인사(.lead) 존재")

    # 9. 시점 명시 + 변동 고지
    rep.add("기준" in body, "시점 명시('~기준') 존재")
    rep.add("변경될 수 있음" in body, "'수치는 변경될 수 있음' 고지 존재")

    # 10. 네이버 호환 — 어두운 배경 + 밝은 글자 조합
    dark = DARK_HEX.search(html) and LIGHT_TEXT.search(html)
    rep.add(not dark, "네이버 호환: 어두운배경+밝은글자 조합 없음",
            "배경이 날아가면 글자가 안 보임 (v6.1)" if dark else "")

    # 11. linear-gradient — 네이버에서 미반영
    n_grad = len(re.findall(r"linear-gradient", html, re.I))
    rep.add(n_grad == 0, "linear-gradient 미사용", f"{n_grad}건 (네이버 미반영)" if n_grad else "", warn=True)

    # 12. .hl 남발 (문단당 1~2개)
    n_hl = len(re.findall(r'class="[^"]*\bhl\b', html))
    n_p = len(re.findall(r"<p\b", html, re.I))
    rep.add(n_p == 0 or n_hl <= n_p * 2, "형광펜(.hl) 남발 아님",
            f".hl {n_hl}개 / <p> {n_p}개", warn=True)

    return rep.render()


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"파일 없음: {path}")
        return 2
    print(f"=== 퍼플앤트 셀프체크: {path.name} ===\n")
    return 1 if check(path) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # `| head` 로 잘라 볼 때
        sys.exit(0)
