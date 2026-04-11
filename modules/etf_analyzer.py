"""Claude AI-powered global ETF portfolio analysis and trend generator."""

import json
import re
import anthropic
from datetime import datetime
from config import CLAUDE_MODEL


_SYSTEM_PROMPT = """당신은 글로벌 매크로 경제와 ETF 투자 전략을 전문으로 하는 포트폴리오 매니저입니다.
매주 글로벌 시장 트렌드를 분석하고, 미국 상장 ETF 기반의 최적 포트폴리오를 추천합니다.
응답은 반드시 유효한 JSON 형식으로만 반환하세요. 마크다운 코드 블록(```) 없이 순수 JSON만 반환하세요."""


def _clean_json(text: str) -> str:
    """Strip markdown fences and whitespace from Claude's response."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_etf_analysis(api_key: str, previous_portfolio: list | None = None) -> dict:
    """Call Claude to generate a weekly ETF portfolio recommendation.

    Args:
        api_key: Anthropic API key.
        previous_portfolio: List of dicts from last week's portfolio, or None.

    Returns:
        Parsed dict with keys: week_label, topic, portfolio, rebalancing,
        market_outlook.

    Raises:
        Exception: On API failure or JSON parse failure.
    """
    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now().strftime("%Y년 %m월 %d일 (%A)")

    prev_section = ""
    if previous_portfolio:
        prev_lines = "\n".join(
            f"  - {e['ticker']} ({e.get('name', '')}) : {e['weight']}%"
            for e in previous_portfolio
        )
        prev_section = f"\n\n## 지난 주 포트폴리오\n{prev_lines}\n"

    prompt = f"""오늘 날짜: {today}
{prev_section}
글로벌 거시경제 환경을 분석하여 이번 주 ETF 투자 포트폴리오를 추천해주세요.
마크다운 없이 아래 JSON 형식으로만 응답하세요. 각 문자열은 간결하게 작성하세요.

{{
  "week_label": "2026년 00주차 (0월 0주)",
  "topic": {{
    "title": "핵심 테마 제목 (20자 이내)",
    "summary": "테마 배경 요약 (2문장)",
    "key_points": ["포인트1", "포인트2", "포인트3"],
    "news_search_queries": [
      {{"query": "영어 검색어1", "description": "한국어 설명"}},
      {{"query": "영어 검색어2", "description": "한국어 설명"}},
      {{"query": "영어 검색어3", "description": "한국어 설명"}}
    ],
    "youtube_search_queries": [
      {{"query": "영어 검색어1", "description": "한국어 설명"}},
      {{"query": "영어 검색어2", "description": "한국어 설명"}}
    ]
  }},
  "portfolio": [
    {{"ticker": "SPY", "name": "ETF명", "weight": 25.0, "category": "주식", "rationale": "선택이유 (1~2문장)", "risk_level": "낮음"}}
  ],
  "rebalancing": {{
    "action": "유지 또는 소폭 조정 또는 전략 변경",
    "changes": [
      {{"ticker": "티커", "action": "증가 또는 감소 또는 신규 편입 또는 제거", "delta_weight": 0.0, "reason": "이유"}}
    ],
    "overall_comment": "전략 코멘트 (1~2문장)"
  }},
  "market_outlook": {{
    "risk_level": "낮음 또는 중간 또는 높음",
    "sentiment": "강세 또는 중립 또는 약세",
    "key_risks": ["리스크1", "리스크2"],
    "opportunities": ["기회1", "기회2"]
  }}
}}

규칙: ETF 5~6개, 비중 합계 정확히 100.0, 미국 상장 ETF만 사용 (SPY QQQ TLT GLD IWM EEM XLK XLE XLF XLV SOXX HYG GLD SLV VNQ ICLN LIT CIBR EMB 등)"""

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _clean_json(message.content[0].text)

    # 응답이 잘린 경우 JSON 복구 시도
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 잘린 JSON 끝에 닫는 괄호를 추가해서 복구 시도
        for closing in ["}}}}}", "}}}}", "}}}", "}}", "}"]:
            try:
                data = json.loads(raw + closing)
                break
            except json.JSONDecodeError:
                continue
        else:
            raise json.JSONDecodeError(
                f"Claude 응답을 JSON으로 파싱할 수 없습니다. 응답 일부: {raw[:200]}",
                raw, 0
            )

    # Normalize weight sum to 100 if floating-point drift
    total = sum(e["weight"] for e in data.get("portfolio", []))
    if total and abs(total - 100.0) > 0.1:
        for e in data["portfolio"]:
            e["weight"] = round(e["weight"] / total * 100, 1)

    return data
