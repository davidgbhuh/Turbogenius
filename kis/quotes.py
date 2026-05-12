"""KIS 시세 API wrappers — 국내주식/ETF 현재가, 기간별 시세."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .client import KISClient

MARKET_DIV_KOSPI = "J"  # KIS 표기상 ETF/일반주식 공통으로 'J'


def get_current_price(client: KISClient, code: str) -> dict:
    """국내주식 현재가 시세 (TR: FHKST01010100)."""
    data = client.get(
        "/uapi/domestic-stock/v1/quotations/inquire-price",
        tr_id="FHKST01010100",
        params={
            "FID_COND_MRKT_DIV_CODE": MARKET_DIV_KOSPI,
            "FID_INPUT_ISCD": code,
        },
    )
    out = data.get("output", {})
    return {
        "code": code,
        "name": out.get("rprs_mrkt_kor_name") or out.get("bstp_kor_isnm") or "",
        "price": _to_float(out.get("stck_prpr")),
        "change": _to_float(out.get("prdy_vrss")),
        "change_pct": _to_float(out.get("prdy_ctrt")),
        "volume": _to_float(out.get("acml_vol")),
        "high": _to_float(out.get("stck_hgpr")),
        "low": _to_float(out.get("stck_lwpr")),
        "open": _to_float(out.get("stck_oprc")),
        "prev_close": _to_float(out.get("stck_sdpr")),
    }


def get_daily_prices(
    client: KISClient,
    code: str,
    start: date,
    end: date | None = None,
    period: str = "D",
    adjusted: bool = True,
) -> pd.DataFrame:
    """국내주식 기간별 시세 (TR: FHKST03010100).

    period: D(일), W(주), M(월), Y(년).
    KIS는 한 번에 최대 ~100건만 반환하므로 100영업일 단위로 끊어 조회합니다.
    """
    if end is None:
        end = date.today()
    if start > end:
        raise ValueError("start 가 end 보다 큽니다")

    frames: list[pd.DataFrame] = []
    chunk_end = end
    # 일자 기준 100거래일 ≒ 약 140일 캘린더, 안전하게 130일씩 끊음
    delta_days = {"D": 130, "W": 700, "M": 3000, "Y": 36500}.get(period, 130)

    while chunk_end >= start:
        chunk_start = max(start, chunk_end - timedelta(days=delta_days))
        df = _fetch_chunk(client, code, chunk_start, chunk_end, period, adjusted)
        if df.empty:
            break
        frames.append(df)
        oldest = df["date"].min()
        # pandas Timestamp 를 datetime.date 로 정규화 — pandas 2.x 는
        # Timestamp 와 date 의 직접 비교를 TypeError 로 거부합니다.
        if hasattr(oldest, "date"):
            oldest = oldest.date()
        next_end = oldest - timedelta(days=1)
        if next_end >= chunk_end:
            break
        chunk_end = next_end

    if not frames:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    result = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )
    result = result[(result["date"] >= pd.Timestamp(start)) & (result["date"] <= pd.Timestamp(end))]
    return result.reset_index(drop=True)


def _fetch_chunk(
    client: KISClient,
    code: str,
    start: date,
    end: date,
    period: str,
    adjusted: bool,
) -> pd.DataFrame:
    data = client.get(
        "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        tr_id="FHKST03010100",
        params={
            "FID_COND_MRKT_DIV_CODE": MARKET_DIV_KOSPI,
            "FID_INPUT_ISCD": code,
            "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0" if adjusted else "1",
        },
    )
    rows = data.get("output2") or []
    records: list[dict] = []
    for row in rows:
        d = row.get("stck_bsop_date")
        if not d:
            continue
        records.append(
            {
                "date": pd.Timestamp(d),
                "open": _to_float(row.get("stck_oprc")),
                "high": _to_float(row.get("stck_hgpr")),
                "low": _to_float(row.get("stck_lwpr")),
                "close": _to_float(row.get("stck_clpr")),
                "volume": _to_float(row.get("acml_vol")),
            }
        )
    if not records:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    return pd.DataFrame(records)


def _to_float(value) -> float:
    if value in (None, "", "-"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
