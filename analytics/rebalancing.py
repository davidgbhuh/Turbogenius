"""리밸런싱(드리프트) 계산 — 현재 보유 vs 목표 비중."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RebalanceRow:
    code: str
    name: str
    target_weight: float
    current_weight: float
    target_value: float
    current_value: float
    delta_value: float  # +면 매수, -면 매도
    current_shares: float
    current_price: float
    suggested_trade_shares: float  # +매수 / -매도

    @property
    def delta_weight(self) -> float:
        return self.current_weight - self.target_weight


def build_rebalance_table(
    holdings: dict[str, float],  # code -> shares
    prices: dict[str, float],  # code -> latest close
    target_weights: dict[str, float],
    names: dict[str, str],
    extra_cash: float = 0.0,
) -> pd.DataFrame:
    """현재 보유 + 추가 입금을 합쳐 목표 비중에 맞추는 매매 권고 표를 만듭니다."""
    codes = sorted(set(holdings) | set(target_weights))
    rows: list[RebalanceRow] = []

    current_values: dict[str, float] = {}
    for code in codes:
        shares = float(holdings.get(code, 0.0))
        price = float(prices.get(code, 0.0))
        current_values[code] = shares * price

    total_value = sum(current_values.values()) + max(extra_cash, 0.0)
    if total_value <= 0:
        return pd.DataFrame()

    for code in codes:
        target_w = float(target_weights.get(code, 0.0))
        current_v = current_values[code]
        current_w = current_v / total_value if total_value else 0.0
        target_v = total_value * target_w
        delta_v = target_v - current_v
        price = float(prices.get(code, 0.0))
        suggested = (delta_v / price) if price > 0 else 0.0
        rows.append(
            RebalanceRow(
                code=code,
                name=names.get(code, code),
                target_weight=target_w,
                current_weight=current_w,
                target_value=target_v,
                current_value=current_v,
                delta_value=delta_v,
                current_shares=float(holdings.get(code, 0.0)),
                current_price=price,
                suggested_trade_shares=suggested,
            )
        )

    df = pd.DataFrame([r.__dict__ for r in rows])
    df["delta_weight"] = df["current_weight"] - df["target_weight"]
    df = df.sort_values(["target_weight", "current_value"], ascending=[False, False])
    return df.reset_index(drop=True)


def aggregate_by_asset_class(
    weights: dict[str, float],
    asset_class_map: dict[str, str],
) -> dict[str, float]:
    """ETF 비중을 자산군 단위로 합산합니다."""
    out: dict[str, float] = {}
    for code, w in weights.items():
        cls = asset_class_map.get(code, "기타")
        out[cls] = out.get(cls, 0.0) + w
    return out
