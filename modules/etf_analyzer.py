"""Claude AI 기반 한국 ETF 분기별 포트폴리오 분석 — tool_use 방식."""

import anthropic
from datetime import datetime
from config import CLAUDE_MODEL


_SYSTEM_PROMPT = """당신은 한국 및 글로벌 거시경제와 ETF 투자 전략을 전문으로 하는 포트폴리오 매니저입니다.
분기마다 글로벌·국내 시장 트렌드를 분석하고, 한국거래소(KRX) 상장 ETF 기반의 최적 포트폴리오를 추천합니다."""


def _current_quarter(now: datetime) -> str:
    q = (now.month - 1) // 3 + 1
    month_range = {1: "1~3월", 2: "4~6월", 3: "7~9월", 4: "10~12월"}[q]
    return f"{now.year}년 {q}분기 ({month_range})"


_TOOL = {
    "name": "submit_portfolio",
    "description": "분기별 한국 ETF 포트폴리오 분석 결과를 제출합니다.",
    "input_schema": {
        "type": "object",
        "required": ["quarter_label", "topic", "portfolio", "rebalancing", "market_outlook"],
        "properties": {
            "quarter_label": {
                "type": "string",
                "description": "예: 2026년 2분기 (4~6월)",
            },
            "topic": {
                "type": "object",
                "required": ["title", "summary", "key_points",
                             "news_search_queries", "youtube_search_queries"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "이번 분기 핵심 투자 테마 제목 (20자 이내)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "테마 배경 요약 (2~3문장)",
                    },
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
                                "query": {"type": "string",
                                          "description": "영어 Google News 검색어"},
                                "description": {"type": "string",
                                                "description": "한국어 설명"},
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
                                "query": {"type": "string",
                                          "description": "영어 YouTube 검색어"},
                                "description": {"type": "string",
                                                "description": "한국어 설명"},
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
                "maxItems": 7,
                "items": {
                    "type": "object",
                    "required": ["ticker", "name", "weight",
                                 "category", "rationale", "risk_level"],
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "KRX 6자리 ETF 코드 (예: 069500)",
                        },
                        "name": {
                            "type": "string",
                            "description": "ETF 한국어 이름 (예: KODEX 200)",
                        },
                        "weight": {
                            "type": "number",
                            "description": "비중 (%), 전체 합계 100",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["국내주식", "해외주식", "채권", "원자재", "리츠", "테마"],
                        },
                        "rationale": {
                            "type": "string",
                            "description": "선택 이유 (1~2문장)",
                        },
                        "risk_level": {
                            "type": "string",
                            "enum": ["낮음", "중간", "높음"],
                        },
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
                                                 "enum": ["증가", "감소",
                                                          "신규 편입", "제거"]},
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
                    "risk_level":    {"type": "string",
                                      "enum": ["낮음", "중간", "높음"]},
                    "sentiment":     {"type": "string",
                                      "enum": ["강세", "중립", "약세"]},
                    "key_risks":     {"type": "array",
                                      "items": {"type": "string"},
                                      "minItems": 2, "maxItems": 3},
                    "opportunities": {"type": "array",
                                      "items": {"type": "string"},
                                      "minItems": 2, "maxItems": 3},
                },
            },
        },
    },
}


# 추천 ETF 풀 (KRX 상장)
_ETF_POOL = """
[국내주식]
069500 KODEX 200, 102110 TIGER 200, 229200 KODEX 코스닥150,
278530 KODEX 200TR, 252670 KODEX 200선물인버스2X

[해외주식]
379800 KODEX 미국S&P500TR, 379810 KODEX 미국나스닥100TR,
360750 TIGER 미국S&P500, 381170 TIGER 미국테크TOP10INDXX,
195930 TIGER 해외상장리츠(합성H), 143850 TIGER 미국달러단기채권액티브,
192090 TIGER 차이나CSI300, 441800 TIGER 인도니프티50

[채권]
114820 KODEX 국채3년, 305080 TIGER 미국채10년선물,
153130 KODEX 단기채권PLUS, 136340 KODEX 단기채권,
459580 KODEX CD금리액티브(합성)

[원자재]
132030 KODEX 골드선물(H), 261220 KODEX WTI원유선물(H),
411060 KODEX 골드선물레버리지(H)

[테마/섹터]
091160 KODEX 반도체, 305720 KODEX 2차전지산업,
305540 TIGER 글로벌리튬&2차전지SOLACTIVE,
139260 TIGER 200 IT, 098560 TIGER 방산,
485540 KODEX 미국AI테크TOP10

[리츠]
182480 TIGER 리츠부동산인프라
"""


def generate_etf_analysis(api_key: str,
                           previous_portfolio: list | None = None) -> dict:
    """Claude tool_use로 분기별 한국 ETF 포트폴리오 분석을 생성합니다.

    Args:
        api_key: Anthropic API key.
        previous_portfolio: 지난 분기 포트폴리오 리스트 (없으면 None).

    Returns:
        quarter_label, topic, portfolio, rebalancing, market_outlook 키를 가진 dict.
    """
    client = anthropic.Anthropic(api_key=api_key)
    now = datetime.now()
    today = now.strftime("%Y년 %m월 %d일")
    quarter = _current_quarter(now)

    prev_section = ""
    if previous_portfolio:
        prev_lines = "\n".join(
            f"  - {e['ticker']} {e.get('name', '')} : {e['weight']}%"
            for e in previous_portfolio
        )
        prev_section = f"\n\n지난 분기 포트폴리오:\n{prev_lines}"

    prompt = (
        f"오늘 날짜: {today} / 현재 분기: {quarter}{prev_section}\n\n"
        f"글로벌 및 국내 거시경제 환경을 분석하여 {quarter} 최적의 "
        f"한국거래소(KRX) 상장 ETF 포트폴리오를 추천해주세요.\n\n"
        f"아래 ETF 풀 중에서 선택하세요 (5~7개, 비중 합계 100%):\n"
        f"{_ETF_POOL}\n\n"
        "지난 분기 포트폴리오가 있으면 변경 이유를 rebalancing에 명확히 설명하세요."
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "submit_portfolio"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_block = next(
        (b for b in message.content if b.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise RuntimeError("Claude가 tool_use 응답을 반환하지 않았습니다.")

    data = tool_block.input

    # 비중 합계 정규화
    total = sum(e["weight"] for e in data.get("portfolio", []))
    if total and abs(total - 100.0) > 0.1:
        for e in data["portfolio"]:
            e["weight"] = round(e["weight"] / total * 100, 1)

    return data
