"""Streamlit 페이지 공용 헬퍼."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from kis import KISClient, KISError, get_daily_prices

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data(show_spinner=False)
def load_etf_list() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "etf_list.csv", dtype={"code": str})


@st.cache_resource(show_spinner=False)
def get_client() -> KISClient | None:
    try:
        return KISClient()
    except KISError as e:
        st.session_state["_kis_error"] = str(e)
        return None


@st.cache_data(show_spinner=False, ttl=60 * 30)
def fetch_daily(code: str, start: date, end: date) -> pd.DataFrame:
    client = get_client()
    if client is None:
        return pd.DataFrame()
    df = get_daily_prices(client, code, start, end, period="D")
    if df.empty:
        return df
    return df.set_index("date")


def fetch_close_panel(codes: list[str], start: date, end: date) -> pd.DataFrame:
    """여러 종목의 종가를 한 DataFrame(컬럼=종목코드)으로 합칩니다."""
    series: dict[str, pd.Series] = {}
    for code in codes:
        df = fetch_daily(code, start, end)
        if df.empty:
            continue
        series[code] = df["close"]
    if not series:
        return pd.DataFrame()
    panel = pd.concat(series, axis=1)
    panel.index = pd.to_datetime(panel.index)
    return panel.sort_index()


def require_client() -> KISClient | None:
    client = get_client()
    if client is None:
        st.error(
            "KIS API 자격증명이 없습니다. `.env` 파일에 `KIS_APP_KEY` / `KIS_APP_SECRET` 를 설정한 뒤 앱을 다시 시작하세요."
        )
        err = st.session_state.get("_kis_error")
        if err:
            st.caption(err)
        st.stop()
    return client


def default_date_range(years: int = 1) -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=365 * years)
    return start, end


def etf_selector(label: str, default_codes: list[str] | None = None, multi: bool = False, key: str | None = None):
    etfs = load_etf_list()
    options = etfs["code"].tolist()
    labels = {row.code: f"{row.code} · {row['name']}" for _, row in etfs.iterrows()}
    fmt = lambda c: labels.get(c, c)
    if multi:
        return st.multiselect(label, options, default=default_codes or [], format_func=fmt, key=key)
    idx = 0
    if default_codes and default_codes[0] in options:
        idx = options.index(default_codes[0])
    return st.selectbox(label, options, index=idx, format_func=fmt, key=key)
