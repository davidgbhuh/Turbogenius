"""Fetch Korean stock listings from KRX via pykrx."""

import streamlit as st
from pykrx import stock as krx
import pandas as pd
from datetime import datetime


@st.cache_data(ttl=3600)
def get_stock_list(market: str) -> pd.DataFrame:
    """Return DataFrame with columns [ticker, name] for the given market.

    Args:
        market: 'KOSPI' or 'KOSDAQ'

    Returns:
        DataFrame with 'ticker' and 'name' columns.
    """
    today = datetime.now().strftime("%Y%m%d")
    try:
        tickers = krx.get_market_ticker_list(today, market=market)
        records = []
        for ticker in tickers:
            name = krx.get_market_ticker_name(ticker)
            records.append({"ticker": ticker, "name": name})
        return pd.DataFrame(records)
    except Exception:
        # Fallback: return well-known tickers so the app still works
        fallback = {
            "KOSPI": [
                {"ticker": "005930", "name": "삼성전자"},
                {"ticker": "000660", "name": "SK하이닉스"},
                {"ticker": "005380", "name": "현대차"},
                {"ticker": "051910", "name": "LG화학"},
                {"ticker": "035420", "name": "NAVER"},
            ],
            "KOSDAQ": [
                {"ticker": "035720", "name": "카카오"},
                {"ticker": "247540", "name": "에코프로비엠"},
                {"ticker": "086520", "name": "에코프로"},
                {"ticker": "196170", "name": "알테오젠"},
                {"ticker": "091990", "name": "셀트리온헬스케어"},
            ],
        }
        return pd.DataFrame(fallback.get(market, []))


def search_stocks(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter stock list by ticker code or company name."""
    if not query:
        return df
    q = query.strip().lower()
    mask = df["ticker"].str.contains(q, case=False) | df["name"].str.contains(q, case=False)
    return df[mask].reset_index(drop=True)
