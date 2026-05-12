"""한국투자증권(KIS) 모의투자 OpenAPI 클라이언트.

KIS Developers (https://apiportal.koreainvestment.com) 모의투자 환경 기준.

필요한 Streamlit Secrets / 환경변수:
    KIS_APP_KEY     : 한국투자증권 OpenAPI App Key
    KIS_APP_SECRET  : 한국투자증권 OpenAPI App Secret

지원 기능:
    - 현재가 / 일자별 시세
    - 종목별 투자자(외국인/기관/개인) 순매수 동향
    - ETF 구성종목(PDF) 조회
    - ETF NAV 추이 및 괴리율
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

# ── 모의투자 엔드포인트 ──────────────────────────────────────────────────────────
_BASE_URL = "https://openapivts.koreainvestment.com:29443"
_TIMEOUT  = 8


# ── 자격증명 ────────────────────────────────────────────────────────────────────

def _get_credentials() -> tuple[str, str]:
    """Secrets/환경변수에서 KIS appkey/appsecret를 읽어온다."""
    try:
        appkey    = st.secrets["KIS_APP_KEY"]
        appsecret = st.secrets["KIS_APP_SECRET"]
        return appkey, appsecret
    except Exception:
        return os.getenv("KIS_APP_KEY", ""), os.getenv("KIS_APP_SECRET", "")


def is_configured() -> bool:
    """KIS API 키가 설정되었는지 확인."""
    appkey, appsecret = _get_credentials()
    return bool(appkey and appsecret)


# ── 토큰 관리 (세션 캐시, 만료 1시간 전 갱신) ───────────────────────────────────

def _get_access_token() -> str | None:
    """OAuth access_token을 반환. 캐시된 토큰이 유효하면 재사용."""
    if not is_configured():
        return None

    cached = st.session_state.get("_kis_token")
    if cached and cached.get("expires_at", 0) > time.time() + 3600:
        return cached["token"]

    appkey, appsecret = _get_credentials()
    try:
        resp = requests.post(
            f"{_BASE_URL}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey":     appkey,
                "appsecret":  appsecret,
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        token = data.get("access_token")
        if not token:
            return None
        # 만료시간 계산 (보통 86400초)
        expires_in = int(data.get("expires_in", 86400))
        st.session_state["_kis_token"] = {
            "token":      token,
            "expires_at": time.time() + expires_in,
        }
        return token
    except Exception:
        return None


# ── 공통 GET 호출 ───────────────────────────────────────────────────────────────

def _get(path: str, tr_id: str, params: dict) -> dict | None:
    """KIS API GET 요청 wrapper. 실패 시 None 반환."""
    token = _get_access_token()
    if not token:
        return None

    appkey, appsecret = _get_credentials()
    headers = {
        "content-type":  "application/json",
        "authorization": f"Bearer {token}",
        "appkey":        appkey,
        "appsecret":     appsecret,
        "tr_id":         tr_id,
        "custtype":      "P",  # 개인
    }
    try:
        resp = requests.get(
            f"{_BASE_URL}{path}",
            headers=headers,
            params=params,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        body = resp.json()
        if body.get("rt_cd") != "0":
            return None
        return body
    except Exception:
        return None


# ── 현재가 ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def get_current_price(ticker: str) -> dict | None:
    """ETF/주식 현재가 정보를 반환.

    Returns:
        {price, change, change_rate, volume, nav, high, low, open}
        실패 시 None.
    """
    body = _get(
        "/uapi/domestic-stock/v1/quotations/inquire-price",
        tr_id="FHKST01010100",
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker},
    )
    if not body:
        return None
    out = body.get("output") or {}
    if not out:
        return None

    def _f(key: str) -> float | None:
        v = out.get(key)
        try:
            return float(str(v).replace(",", "")) if v not in (None, "") else None
        except (ValueError, TypeError):
            return None

    return {
        "price":       _f("stck_prpr"),       # 현재가
        "change":      _f("prdy_vrss"),       # 전일대비
        "change_rate": _f("prdy_ctrt"),       # 전일대비율 (%)
        "volume":      _f("acml_vol"),        # 누적거래량
        "nav":         _f("nav"),             # ETF NAV (없을 수 있음)
        "high":        _f("stck_hgpr"),       # 고가
        "low":         _f("stck_lwpr"),       # 저가
        "open":        _f("stck_oprc"),       # 시가
        "prev_close":  _f("stck_sdpr"),       # 기준가(전일종가)
    }


# ── 일별 시세 (기간별 — 일/주/월) ───────────────────────────────────────────────

@st.cache_data(ttl=1800)
def get_daily_prices(ticker: str, period: str = "D", count: int = 100) -> pd.DataFrame:
    """일별 OHLCV를 DataFrame으로 반환.

    Args:
        ticker: 6자리 종목코드.
        period: "D"=일봉, "W"=주봉, "M"=월봉.
        count:  최대 100건 (KIS 제약).

    Returns:
        DataFrame — columns: date, open, high, low, close, volume.
        실패 시 empty DataFrame.
    """
    end_date   = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=count * 2)).strftime("%Y%m%d")
    body = _get(
        "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        tr_id="FHKST03010100",
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD":         ticker,
            "FID_INPUT_DATE_1":       start_date,
            "FID_INPUT_DATE_2":       end_date,
            "FID_PERIOD_DIV_CODE":    period,
            "FID_ORG_ADJ_PRC":        "0",  # 수정주가 반영
        },
    )
    if not body:
        return pd.DataFrame()
    rows = body.get("output2") or []
    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        try:
            records.append({
                "date":   pd.to_datetime(r.get("stck_bsop_date"), format="%Y%m%d"),
                "open":   float(r.get("stck_oprc", 0) or 0),
                "high":   float(r.get("stck_hgpr", 0) or 0),
                "low":    float(r.get("stck_lwpr", 0) or 0),
                "close":  float(r.get("stck_clpr", 0) or 0),
                "volume": float(r.get("acml_vol",  0) or 0),
            })
        except (ValueError, TypeError):
            continue

    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    return df


# ── 종목별 투자자 매매동향 ─────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def get_investor_flow(ticker: str) -> pd.DataFrame:
    """일자별 외국인/기관/개인 순매수 거래량(주).

    KIS `inquire-investor` API. 최근 약 30영업일치 반환.

    Returns:
        DataFrame — columns: date, foreign_net, institutional_net, individual_net.
        값은 순매수 주식 수 (음수 = 순매도).
    """
    body = _get(
        "/uapi/domestic-stock/v1/quotations/inquire-investor",
        tr_id="FHKST01010900",
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker},
    )
    if not body:
        return pd.DataFrame()
    rows = body.get("output") or []
    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        try:
            records.append({
                "date":              pd.to_datetime(r.get("stck_bsop_date"), format="%Y%m%d"),
                "foreign_net":       int(float(r.get("frgn_ntby_qty",   0) or 0)),
                "institutional_net": int(float(r.get("orgn_ntby_qty",   0) or 0)),
                "individual_net":    int(float(r.get("prsn_ntby_qty",   0) or 0)),
            })
        except (ValueError, TypeError):
            continue

    return pd.DataFrame(records).sort_values("date").reset_index(drop=True)


# ── ETF 구성종목 ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_etf_components(ticker: str) -> pd.DataFrame:
    """ETF 구성종목(PDF) 리스트.

    Returns:
        DataFrame — columns: code, name, weight (%), shares, value.
        실패/비ETF 종목은 empty.
    """
    body = _get(
        "/uapi/etfetn/v1/quotations/inquire-component-stock-price",
        tr_id="FHKST121600C0",
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE":  "11216",
            "FID_INPUT_ISCD":         ticker,
        },
    )
    if not body:
        return pd.DataFrame()
    rows = body.get("output2") or body.get("output") or []
    if not rows:
        return pd.DataFrame()

    records = []
    for r in rows:
        try:
            records.append({
                "code":   r.get("stck_shrn_iscd", "") or r.get("shtn_pdno", ""),
                "name":   r.get("hts_kor_isnm",   "") or r.get("prdt_name", ""),
                "weight": float(str(r.get("etf_cnfg_issu_rlim", "0")).replace(",", "") or 0),
                "shares": float(str(r.get("etf_cnfg_issu_cnt",  "0")).replace(",", "") or 0),
                "price":  float(str(r.get("stck_prpr",          "0")).replace(",", "") or 0),
            })
        except (ValueError, TypeError):
            continue

    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.sort_values("weight", ascending=False).reset_index(drop=True)


# ── ETF NAV / 괴리율 ───────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def get_etf_nav_trend(ticker: str) -> pd.DataFrame:
    """ETF NAV 일별 추이.

    `inquire-daily-itemchartprice`로 가격을 받고, 동일 호출의 NAV 필드를 활용.
    KIS에서 NAV 전용 trend API가 모의투자에서 지원되지 않을 수 있어,
    현재가 API의 `nav` 필드와 일별 종가를 비교해 괴리율을 추정.

    Returns:
        DataFrame — columns: date, close, nav, premium (%).
    """
    # 1차: 전용 NAV API 시도
    body = _get(
        "/uapi/etfetn/v1/quotations/nav-comparison-daily-trend",
        tr_id="FHPST02440000",
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD":         ticker,
        },
    )
    rows = (body.get("output2") or body.get("output") or []) if body else []
    if rows:
        records = []
        for r in rows:
            try:
                close = float(str(r.get("stck_clpr", 0) or 0).replace(",", ""))
                nav   = float(str(r.get("nav",        0) or 0).replace(",", ""))
                if close <= 0 or nav <= 0:
                    continue
                records.append({
                    "date":    pd.to_datetime(r.get("stck_bsop_date"), format="%Y%m%d"),
                    "close":   close,
                    "nav":     nav,
                    "premium": round((close / nav - 1) * 100, 3),
                })
            except (ValueError, TypeError):
                continue
        if records:
            return pd.DataFrame(records).sort_values("date").reset_index(drop=True)

    # Fallback: 일별 종가 + 현재 NAV로 단일 시점 추정 (전체 추이 없음)
    return pd.DataFrame()


# ── 헬퍼: 배치 현재가 ───────────────────────────────────────────────────────────

def get_prices_batch(tickers: tuple[str, ...]) -> dict[str, dict]:
    """여러 종목 현재가를 한 번에 조회 (개별 API 순차 호출).

    Returns: {ticker: {price, change, change_rate, nav, ...}}
    """
    result = {}
    for t in tickers:
        info = get_current_price(t)
        if info:
            result[t] = info
    return result
