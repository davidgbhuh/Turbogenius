"""Korean stock listings via KRX public API, with hardcoded fallback."""

import streamlit as st
import pandas as pd
import requests

# KRX public API endpoint
_KRX_URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
_KRX_HEADERS = {
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
_KRX_MARKET_ID = {"KOSPI": "STK", "KOSDAQ": "KSQ"}


def _fetch_from_krx(market: str) -> pd.DataFrame:
    """Fetch full stock list from KRX public API."""
    resp = requests.post(
        _KRX_URL,
        headers=_KRX_HEADERS,
        data={
            "bld": "dbms/MDC/STAT/standard/MDCSTAT01901",
            "mktId": _KRX_MARKET_ID[market],
            "share": "1",
            "csvxls_isNo": "false",
        },
        timeout=8,
    )
    resp.raise_for_status()
    items = resp.json().get("OutBlock_1", [])
    records = [
        {"ticker": item["ISU_SRT_CD"], "name": item["ISU_ABBRV"]}
        for item in items
        if item.get("ISU_SRT_CD") and item.get("ISU_ABBRV")
    ]
    return pd.DataFrame(records)


# ── Fallback hardcoded list ───────────────────────────────────────────────────
_FALLBACK = {
    "KOSPI": [
        ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("005380", "현대차"),
        ("005490", "POSCO홀딩스"), ("051910", "LG화학"), ("035420", "NAVER"),
        ("000270", "기아"), ("068270", "셀트리온"), ("105560", "KB금융"),
        ("055550", "신한지주"), ("012330", "현대모비스"), ("028260", "삼성물산"),
        ("066570", "LG전자"), ("032830", "삼성생명"), ("017670", "SK텔레콤"),
        ("030200", "KT"), ("003550", "LG"), ("096770", "SK이노베이션"),
        ("009150", "삼성전기"), ("018260", "삼성에스디에스"),
        ("373220", "LG에너지솔루션"), ("207940", "삼성바이오로직스"),
        ("000810", "삼성화재"), ("034730", "SK"), ("011200", "HMM"),
        ("086790", "하나금융지주"), ("316140", "우리금융지주"), ("024110", "기업은행"),
        ("139480", "이마트"), ("004020", "현대제철"), ("006400", "삼성SDI"),
        ("010950", "S-Oil"), ("011780", "금호석유"), ("003490", "대한항공"),
        ("010130", "고려아연"), ("000100", "유한양행"), ("002790", "아모레퍼시픽"),
        ("011170", "롯데케미칼"), ("004170", "신세계"), ("009540", "HD한국조선해양"),
        ("042660", "한화오션"), ("047050", "포스코인터내셔널"), ("003670", "포스코퓨처엠"),
        ("000120", "CJ대한통운"), ("097950", "CJ제일제당"), ("001040", "CJ"),
        ("021240", "코웨이"), ("011790", "SKC"), ("008770", "호텔신라"),
        ("161390", "한국타이어앤테크놀로지"), ("180640", "한진칼"), ("002380", "KCC"),
        ("000080", "하이트진로"), ("033780", "KT&G"), ("271560", "오리온"),
        ("007310", "오뚜기"), ("004990", "롯데지주"), ("023530", "롯데쇼핑"),
        ("010060", "OCI홀딩스"), ("001450", "현대해상"), ("000990", "DB하이텍"),
        ("005940", "NH투자증권"), ("016360", "삼성증권"), ("071050", "한국금융지주"),
        ("006360", "GS건설"), ("000720", "현대건설"), ("028050", "삼성엔지니어링"),
        ("047040", "대우건설"), ("294870", "HDC현대산업개발"), ("009830", "한화솔루션"),
        ("010620", "현대미포조선"), ("329180", "현대중공업"), ("267250", "HD현대"),
    ],
    "KOSDAQ": [
        ("035720", "카카오"), ("247540", "에코프로비엠"), ("086520", "에코프로"),
        ("196170", "알테오젠"), ("091990", "셀트리온헬스케어"), ("028300", "HLB"),
        ("263750", "펄어비스"), ("041510", "에스엠"), ("035900", "JYP Ent"),
        ("122870", "와이지엔터테인먼트"), ("112040", "위메이드"), ("095660", "네오위즈"),
        ("293490", "카카오게임즈"), ("214150", "클래시스"), ("145020", "휴젤"),
        ("357780", "솔브레인"), ("192820", "코스맥스"), ("000250", "삼천당제약"),
        ("141080", "레고켐바이오"), ("217270", "넵튠"), ("240810", "원익IPS"),
        ("058470", "리노공업"), ("131970", "테크윙"), ("036810", "에프에스티"),
        ("039030", "이오테크닉스"), ("319400", "현대무벡스"), ("054040", "한국전자금융"),
        ("053800", "안랩"), ("078340", "컴투스"), ("036570", "엔씨소프트"),
        ("251270", "넷마블"), ("259960", "크래프톤"), ("352820", "하이브"),
        ("035760", "CJ ENM"), ("041960", "블리자드"), ("067160", "아프리카TV"),
        ("064260", "다날"), ("084010", "대한제강"), ("039200", "오스코텍"),
        ("084370", "유진테크"), ("060850", "에나인"), ("107640", "한국유리공업"),
        ("064550", "바이오니아"), ("016670", "디에이테크놀로지"), ("950130", "엑세스바이오"),
        ("067630", "HLB생명과학"), ("009420", "한올바이오파마"), ("215600", "신라젠"),
        ("214370", "케어젠"), ("048410", "현대바이오"), ("145720", "덴티움"),
        ("140910", "에스티팜"), ("200130", "콜마비앤에이치"), ("208140", "정다운"),
        ("060260", "에이텀"), ("032640", "LG유플러스"), ("010280", "아이티센"),
        ("053210", "스카이라이프"), ("060310", "3S"), ("950160", "코오롱티슈진"),
        ("108675", "LG디스플레이우"), ("237690", "에스티팜"), ("054620", "APS홀딩스"),
        ("078130", "대웅"), ("078160", "메디톡스"), ("091700", "파미셀"),
        ("226950", "올릭스"), ("226340", "본느"), ("145170", "피엔티"),
        ("119610", "인터로조"), ("038870", "에코마케팅"), ("950200", "파나진"),
    ],
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_list(market: str) -> pd.DataFrame:
    """Return DataFrame with [ticker, name] columns.

    Tries KRX public API first; falls back to hardcoded list on failure.
    """
    try:
        df = _fetch_from_krx(market)
        if not df.empty:
            return df
    except Exception:
        pass

    # Fallback
    records = [{"ticker": t, "name": n} for t, n in _FALLBACK.get(market, [])]
    return pd.DataFrame(records)


def search_stocks(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter stock list by ticker code or company name."""
    if not query:
        return df
    q = query.strip().lower()
    mask = (
        df["ticker"].str.contains(q, case=False)
        | df["name"].str.contains(q, case=False)
    )
    return df[mask].reset_index(drop=True)
