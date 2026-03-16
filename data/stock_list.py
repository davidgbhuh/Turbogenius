"""Korean stock listings — uses a curated fallback list (no pykrx required)."""

import streamlit as st
import pandas as pd

# Curated list of major Korean stocks
_KOSPI_STOCKS = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("005380", "현대차"),
    ("005490", "POSCO홀딩스"),
    ("051910", "LG화학"),
    ("035420", "NAVER"),
    ("000270", "기아"),
    ("068270", "셀트리온"),
    ("105560", "KB금융"),
    ("055550", "신한지주"),
    ("012330", "현대모비스"),
    ("028260", "삼성물산"),
    ("066570", "LG전자"),
    ("032830", "삼성생명"),
    ("017670", "SK텔레콤"),
    ("030200", "KT"),
    ("003550", "LG"),
    ("096770", "SK이노베이션"),
    ("009150", "삼성전기"),
    ("018260", "삼성에스디에스"),
    ("373220", "LG에너지솔루션"),
    ("207940", "삼성바이오로직스"),
    ("000810", "삼성화재"),
    ("034730", "SK"),
    ("011200", "HMM"),
    ("086790", "하나금융지주"),
    ("316140", "우리금융지주"),
    ("024110", "기업은행"),
    ("139480", "이마트"),
    ("004020", "현대제철"),
]

_KOSDAQ_STOCKS = [
    ("035720", "카카오"),
    ("247540", "에코프로비엠"),
    ("086520", "에코프로"),
    ("196170", "알테오젠"),
    ("091990", "셀트리온헬스케어"),
    ("028300", "HLB"),
    ("263750", "펄어비스"),
    ("041510", "에스엠"),
    ("035900", "JYP Ent"),
    ("122870", "와이지엔터테인먼트"),
    ("112040", "위메이드"),
    ("095660", "네오위즈"),
    ("293490", "카카오게임즈"),
    ("214150", "클래시스"),
    ("145020", "휴젤"),
    ("054620", "APS홀딩스"),
    ("357780", "솔브레인"),
    ("192820", "코스맥스"),
    ("214370", "케어젠"),
    ("051500", "CJ헬스케어"),
]


@st.cache_data(ttl=3600)
def get_stock_list(market: str) -> pd.DataFrame:
    """Return DataFrame with columns [ticker, name] for the given market."""
    if market == "KOSDAQ":
        records = [{"ticker": t, "name": n} for t, n in _KOSDAQ_STOCKS]
    else:
        records = [{"ticker": t, "name": n} for t, n in _KOSPI_STOCKS]
    return pd.DataFrame(records)


def search_stocks(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter stock list by ticker code or company name."""
    if not query:
        return df
    q = query.strip().lower()
    mask = df["ticker"].str.contains(q, case=False) | df["name"].str.contains(q, case=False)
    return df[mask].reset_index(drop=True)
