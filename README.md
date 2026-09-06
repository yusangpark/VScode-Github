# VScode-Github — 블로그 2축 운영 워크스페이스

퍼플앤트(경제·주식·부동산)와 푸로그(맛집·데이트) 블로그를 한 레포에서 운영하기 위한 클로드 환경 설정.
작업 규칙은 [`CLAUDE.md`](CLAUDE.md)에 있고, 글쓰기 방법론은 계정에 동기화된 스킬 두 개
(`purple-ant-blog-post`, `foorog-content`)에 있음.

## 구성

```
CLAUDE.md                      두 축 공통 규칙 (매 세션 자동 로드)
.mcp.json                      MCP 서버 (playwright, fetch)
.claude/settings.json          권한 허용목록 — 리서치 때 승인 팝업 줄임
scripts/check_post.py          퍼플앤트 HTML 셀프체크 자동화
scripts/tts_count.py           푸로그 숏폼 대본 분량·형식 검사
퍼플앤트 블로그/               HTML 포스팅 + 이미지/ + 포스팅_인덱스.md
푸로그/                        4종 콘텐츠 + _푸로그_말투가이드.md + 콘텐츠_인덱스.md
```

## 처음 한 번만 — MCP 서버 준비물

이 레포를 클론한 컴퓨터에서 클로드 코드를 처음 열면 `.mcp.json`을 신뢰할지 물어봄. 승인하면 붙음.

| 서버 | 필요한 것 | 확인 |
|---|---|---|
| `playwright` | Node.js (npx) | `node -v` |
| `fetch` | uv (uvx) | `uv --version` |

uv가 없으면:

```bash
brew install uv          # 또는
curl -LsSf https://astral.sh/uv/install.sh | sh
```

둘 다 **API 키가 필요 없음.** 첫 실행 때 패키지를 내려받느라 잠깐 걸림.

- **playwright** ([microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)) — 조감도·현장사진을 실제 파일로 저장, 완성 HTML을 네이버에 붙여넣기 전 렌더 확인
- **fetch** ([modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch)) — 기사 원문을 요약 없이 그대로 가져와 숫자 교차확인

## 검증 스크립트

파이썬 3만 있으면 됨(외부 패키지 없음). FAIL이 남은 채로 발행하지 말 것.

```bash
python3 scripts/check_post.py "퍼플앤트 블로그/20260906_주제.html"
python3 scripts/tts_count.py 대본.txt --target 35
```

`check_post.py`는 음슴체 유지·AI티 패턴·사진 번호 연속성·`.verdict` 개수·네이버 붙여넣기 호환성을 봄
(관계자 인용문 `.quote`와 브랜드 인사 "안녕하세요"는 말투 검사에서 제외).
`tts_count.py`는 공백 제외 글자수로 1.0배속 예상 초를 계산하고, 문장 길이와 TTS가 못 읽는 문자를 잡음.

두 스크립트 모두 **기계가 셀 수 있는 항목만** 봄. 팩트 교차확인, 정비사업 단계 정확성, 프레이밍은
여전히 스킬과 사람의 몫임.
