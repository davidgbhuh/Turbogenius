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
글로벌 거시경제 환경을 분석하여 **이번 주 ETF 투자 포트폴리오**를 추천해주세요.

아래 JSON 스키마를 정확히 따르세요. 마크다운 없이 순수 JSON만 반환하세요.

{{
  "week_label": "string  // 예: 2026년 15주차 (4월 2주)",
  "topic": {{
    "title": "string  // 이번 주 핵심 글로벌 투자 테마 (15자 내외)",
    "summary": "string  // 테마 배경 설명 (3~4문장, 한국어)",
    "key_points": ["string", "string", "string"],
    "news_search_queries": [
      {{"query": "string  // 영어 Google News 검색어", "description": "string  // 한국어 설명"}},
      {{"query": "string", "description": "string"}},
      {{"query": "string", "description": "string"}}
    ],
    "youtube_search_queries": [
      {{"query": "string  // 영어 YouTube 검색어", "description": "string  // 한국어 설명"}},
      {{"query": "string", "description": "string"}}
    ]
  }},
  "portfolio": [
    {{
      "ticker": "string  // 미국 상장 ETF 티커 (예: SPY)",
      "name": "string  // ETF 전체 이름",
      "weight": 0.0,  // 비중 (%), 합계 100
      "category": "string  // 주식/채권/원자재/리츠/테마",
      "rationale": "string  // 포함 이유 (2~3문장)",
      "risk_level": "string  // 낮음 | 중간 | 높음"
    }}
  ],
  "rebalancing": {{
    "action": "string  // 유지 | 소폭 조정 | 전략 변경",
    "changes": [
      {{
        "ticker": "string",
        "action": "string  // 증가 | 감소 | 신규 편입 | 제거",
        "delta_weight": 0.0,  // 변경 비중 포인트 (양수/음수)
        "reason": "string"
      }}
    ],
    "overall_comment": "string  // 전반적인 전략 코멘트 (2~3문장)"
  }},
  "market_outlook": {{
    "risk_level": "string  // 낮음 | 중간 | 높음",
    "sentiment": "string  // 강세 | 중립 | 약세",
    "key_risks": ["string", "string"],
    "opportunities": ["string", "string"]
  }}
}}

포트폴리오 구성 규칙:
- ETF 수: 5~8개
- 비중 합계: 정확히 100.0
- 미국 상장 ETF만 사용 (SPY, QQQ, TLT, GLD, IWM, EEM, VGK, XLK, XLE, XLF, XLV,
  XLU, SOXX, ARKK, HYG, LIT, ICLN, CIBR, VNQ, EMB, SHY, IEF, USO, SLV 등)
- 지난 주 포트폴리오가 있을 경우 변경 이유를 rebalancing에 명확히 설명
"""

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _clean_json(message.content[0].text)
    data = json.loads(raw)

    # Normalize weight sum to 100 if floating-point drift
    total = sum(e["weight"] for e in data.get("portfolio", []))
    if total and abs(total - 100.0) > 0.1:
        for e in data["portfolio"]:
            e["weight"] = round(e["weight"] / total * 100, 1)

    return data
