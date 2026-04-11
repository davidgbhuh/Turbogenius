"""Claude AI-powered global ETF portfolio analysis — tool_use 방식으로 JSON 보장."""

import anthropic
from datetime import datetime
from config import CLAUDE_MODEL


_SYSTEM_PROMPT = """당신은 글로벌 매크로 경제와 ETF 투자 전략을 전문으로 하는 포트폴리오 매니저입니다.
매주 글로벌 시장 트렌드를 분석하고, 미국 상장 ETF 기반의 최적 포트폴리오를 추천합니다."""

# ── Tool schema: Claude가 반드시 이 구조로 응답하도록 강제 ──────────────────────
_TOOL = {
    "name": "submit_portfolio",
    "description": "주간 글로벌 ETF 포트폴리오 분석 결과를 제출합니다.",
    "input_schema": {
        "type": "object",
        "required": ["week_label", "topic", "portfolio", "rebalancing", "market_outlook"],
        "properties": {
            "week_label": {
                "type": "string",
                "description": "예: 2026년 15주차 (4월 2주)",
            },
            "topic": {
                "type": "object",
                "required": ["title", "summary", "key_points",
                             "news_search_queries", "youtube_search_queries"],
                "properties": {
                    "title": {"type": "string", "description": "이번 주 핵심 투자 테마 제목 (20자 이내)"},
                    "summary": {"type": "string", "description": "테마 배경 요약 (2~3문장)"},
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "핵심 포인트 3개",
                    },
                    "news_search_queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["query", "description"],
                            "properties": {
                                "query": {"type": "string", "description": "영어 Google News 검색어"},
                                "description": {"type": "string", "description": "한국어 설명"},
                            },
                        },
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "youtube_search_queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["query", "description"],
                            "properties": {
                                "query": {"type": "string", "description": "영어 YouTube 검색어"},
                                "description": {"type": "string", "description": "한국어 설명"},
                            },
                        },
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
            },
            "portfolio": {
                "type": "array",
                "minItems": 5,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "required": ["ticker", "name", "weight", "category", "rationale", "risk_level"],
                    "properties": {
                        "ticker":     {"type": "string", "description": "미국 상장 ETF 티커 (예: SPY)"},
                        "name":       {"type": "string", "description": "ETF 전체 이름"},
                        "weight":     {"type": "number", "description": "비중 (%), 전체 합계 100"},
                        "category":   {"type": "string", "enum": ["주식", "채권", "원자재", "리츠", "테마"]},
                        "rationale":  {"type": "string", "description": "선택 이유 (1~2문장)"},
                        "risk_level": {"type": "string", "enum": ["낮음", "중간", "높음"]},
                    },
                },
            },
            "rebalancing": {
                "type": "object",
                "required": ["action", "changes", "overall_comment"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["유지", "소폭 조정", "전략 변경"],
                    },
                    "changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["ticker", "action", "delta_weight", "reason"],
                            "properties": {
                                "ticker":       {"type": "string"},
                                "action":       {"type": "string",
                                                 "enum": ["증가", "감소", "신규 편입", "제거"]},
                                "delta_weight": {"type": "number"},
                                "reason":       {"type": "string"},
                            },
                        },
                    },
                    "overall_comment": {"type": "string"},
                },
            },
            "market_outlook": {
                "type": "object",
                "required": ["risk_level", "sentiment", "key_risks", "opportunities"],
                "properties": {
                    "risk_level":    {"type": "string", "enum": ["낮음", "중간", "높음"]},
                    "sentiment":     {"type": "string", "enum": ["강세", "중립", "약세"]},
                    "key_risks":     {"type": "array", "items": {"type": "string"},
                                      "minItems": 2, "maxItems": 2},
                    "opportunities": {"type": "array", "items": {"type": "string"},
                                      "minItems": 2, "maxItems": 2},
                },
            },
        },
    },
}


def generate_etf_analysis(api_key: str, previous_portfolio: list | None = None) -> dict:
    """Claude tool_use로 주간 ETF 포트폴리오 분석을 생성합니다.

    tool_use 방식은 Claude가 반드시 정해진 JSON 스키마로만 응답하므로
    파싱 오류가 발생하지 않습니다.

    Args:
        api_key: Anthropic API key.
        previous_portfolio: 지난 주 포트폴리오 리스트 (없으면 None).

    Returns:
        week_label, topic, portfolio, rebalancing, market_outlook 키를 가진 dict.
    """
    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now().strftime("%Y년 %m월 %d일 (%A)")

    prev_section = ""
    if previous_portfolio:
        prev_lines = "\n".join(
            f"  - {e['ticker']} ({e.get('name', '')}) : {e['weight']}%"
            for e in previous_portfolio
        )
        prev_section = f"\n\n지난 주 포트폴리오:\n{prev_lines}"

    prompt = (
        f"오늘 날짜: {today}{prev_section}\n\n"
        "글로벌 거시경제 환경을 분석하여 이번 주 최적의 ETF 포트폴리오를 추천해주세요. "
        "ETF는 5개, 비중 합계 100%, 미국 상장 ETF만 사용하세요 "
        "(SPY, QQQ, TLT, GLD, IWM, EEM, VGK, XLK, XLE, XLF, XLV, "
        "SOXX, HYG, SLV, VNQ, ICLN, LIT, CIBR, EMB 등). "
        "지난 주 포트폴리오가 있으면 변경 이유를 rebalancing에 명확히 설명하세요."
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "submit_portfolio"},
        messages=[{"role": "user", "content": prompt}],
    )

    # tool_use 블록에서 구조화된 데이터 추출 (항상 유효한 dict)
    tool_block = next(
        (b for b in message.content if b.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise RuntimeError("Claude가 tool_use 응답을 반환하지 않았습니다.")

    data = tool_block.input

    # 비중 합계 정규화 (부동소수점 오차 보정)
    total = sum(e["weight"] for e in data.get("portfolio", []))
    if total and abs(total - 100.0) > 0.1:
        for e in data["portfolio"]:
            e["weight"] = round(e["weight"] / total * 100, 1)

    return data
