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
각 텍스트 필드는 반드시 50자 이내로 작성하세요. rationale은 60자 이내.

아래 JSON 구조를 채워 반환하세요:

{{
  "week_label": "2026년 XX주차",
  "topic": {{
    "title": "테마 제목(20자 이내)",
    "summary": "요약(50자 이내)",
    "key_points": ["포인트1(30자이내)", "포인트2(30자이내)", "포인트3(30자이내)"],
    "news_search_queries": [
      {{"query": "english query 1", "description": "설명"}},
      {{"query": "english query 2", "description": "설명"}},
      {{"query": "english query 3", "description": "설명"}}
    ],
    "youtube_search_queries": [
      {{"query": "english query 1", "description": "설명"}},
      {{"query": "english query 2", "description": "설명"}}
    ]
  }},
  "portfolio": [
    {{"ticker": "SPY", "name": "ETF명", "weight": 25.0, "category": "주식", "rationale": "이유(60자이내)", "risk_level": "낮음"}}
  ],
  "rebalancing": {{
    "action": "유지",
    "changes": [{{"ticker": "티커", "action": "증가", "delta_weight": 5.0, "reason": "이유(40자이내)"}}],
    "overall_comment": "코멘트(50자이내)"
  }},
  "market_outlook": {{
    "risk_level": "중간",
    "sentiment": "중립",
    "key_risks": ["리스크1(30자이내)", "리스크2(30자이내)"],
    "opportunities": ["기회1(30자이내)", "기회2(30자이내)"]
  }}
}}

ETF 5개, 비중 합계 100.0, 미국 상장 ETF만 사용."""

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8192,
        system=_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "{"},  # prefill: 순수 JSON 시작 강제
        ],
    )

    # prefill로 시작한 "{" + 나머지 응답 합치기
    raw = "{" + message.content[0].text
    raw = _clean_json(raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Claude 응답 파싱 실패 (응답 앞부분): {raw[:300]}",
            raw, e.pos,
        ) from e

    # Normalize weight sum to 100 if floating-point drift
    total = sum(e["weight"] for e in data.get("portfolio", []))
    if total and abs(total - 100.0) > 0.1:
        for e in data["portfolio"]:
            e["weight"] = round(e["weight"] / total * 100, 1)

    return data
