"""포트폴리오 가치/메트릭 계산."""
from __future__ import annotations

import pandas as pd

from .returns import summary_metrics


def portfolio_value(
    price_panel: pd.DataFrame,
    weights: dict[str, float],
    initial: float = 1_000_000.0,
) -> pd.Series:
    """price_panel: DatetimeIndex, 컬럼=종목코드, 값=종가.

    각 종목에 weight 비율로 initial 금액을 분배해 매수 후 보유한다고 가정합니다.
    """
    if price_panel.empty:
        return pd.Series(dtype=float)

    codes = [c for c in weights if c in price_panel.columns]
    if not codes:
        return pd.Series(dtype=float)

    panel = price_panel[codes].dropna(how="all").ffill().dropna()
    if panel.empty:
        return pd.Series(dtype=float)

    weight_sum = sum(weights[c] for c in codes)
    if weight_sum <= 0:
        return pd.Series(dtype=float)
    norm = {c: weights[c] / weight_sum for c in codes}

    first = panel.iloc[0]
    shares = {c: (initial * norm[c]) / first[c] for c in codes if first[c] > 0}
    value = sum(panel[c] * shares[c] for c in shares)
    value.name = "portfolio"
    return value


def portfolio_metrics(value: pd.Series) -> dict:
    return summary_metrics(value)
