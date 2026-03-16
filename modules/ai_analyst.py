"""Claude AI-powered stock analysis report generator."""

import anthropic
from config import CLAUDE_MODEL


_SYSTEM_PROMPT = """당신은 한국 주식 시장 전문 애널리스트입니다.
주어진 기업 정보와 기술적 지표를 바탕으로 투자자에게 유용한 분석 리포트를 작성합니다.
리포트는 명확하고 구조적으로 작성하며, 구체적인 수치를 포함해야 합니다.
투자 권고는 신중하게 하며, 항상 투자에는 위험이 따름을 명시합니다."""


def _build_prompt(company_info: dict, indicator_summary: dict, period: str) -> str:
    name = company_info.get("name", "알 수 없음")
    sector = company_info.get("sector", "-")
    industry = company_info.get("industry", "-")
    market_cap = company_info.get("market_cap")
    per = company_info.get("per")
    pbr = company_info.get("pbr")

    close = indicator_summary.get("close", 0)
    rsi = indicator_summary.get("RSI")
    macd = indicator_summary.get("MACD")
    macd_sig = indicator_summary.get("MACD_signal")
    bb_upper = indicator_summary.get("BB_upper")
    bb_lower = indicator_summary.get("BB_lower")
    ma5 = indicator_summary.get("MA5")
    ma20 = indicator_summary.get("MA20")
    ma60 = indicator_summary.get("MA60")
    ma120 = indicator_summary.get("MA120")

    def fmt(val, decimals=2):
        if val is None:
            return "N/A"
        return f"{val:,.{decimals}f}"

    prompt = f"""다음 데이터를 바탕으로 {name} 주식 분석 리포트를 작성해주세요.

## 기업 기본 정보
- 종목명: {name}
- 섹터: {sector}
- 업종: {industry}
- 시가총액: {fmt(market_cap, 0) if market_cap else 'N/A'} 원
- PER: {fmt(per, 1)}배
- PBR: {fmt(pbr, 2)}배

## 현재 주가 ({period} 기준 최신 데이터)
- 현재가: {fmt(close, 0)} 원

## 기술적 지표
- 이동평균선: MA5={fmt(ma5, 0)}, MA20={fmt(ma20, 0)}, MA60={fmt(ma60, 0)}, MA120={fmt(ma120, 0)}
- RSI(14): {fmt(rsi, 1)}
- MACD: {fmt(macd, 2)}, Signal: {fmt(macd_sig, 2)}
- 볼린저밴드: 상단={fmt(bb_upper, 0)}, 하단={fmt(bb_lower, 0)}

## 작성 형식
아래 항목을 포함한 마크다운 형식의 리포트를 작성해주세요:

1. **종합 투자의견** (매수/중립/매도 중 하나, 간략한 근거)
2. **기술적 분석 요약** (이동평균, RSI, MACD, 볼린저밴드 해석)
3. **지지선 / 저항선** (구체적인 가격대)
4. **단기 전망 (1~4주)**
5. **중기 전망 (1~3개월)**
6. **주요 리스크 요인**
7. **투자 유의사항** (면책조항)

반드시 한국어로 작성하고, 각 항목에 근거를 포함해주세요.
"""
    return prompt


def generate_report(
    company_info: dict,
    indicator_summary: dict,
    period: str,
    api_key: str,
) -> str:
    """Generate an AI analysis report using Claude.

    Args:
        company_info: Dict from data_fetcher.get_company_info().
        indicator_summary: Dict from technical.get_indicator_summary().
        period: Human-readable period string (e.g. '1년').
        api_key: Anthropic API key.

    Returns:
        Markdown-formatted analysis report string.

    Raises:
        Exception: If the API call fails.
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_prompt(company_info, indicator_summary, period)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text
