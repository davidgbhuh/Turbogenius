"""수익률 및 리스크 메트릭 계산."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().dropna()


def cumulative_returns(prices: pd.Series) -> pd.Series:
    if prices.empty:
        return prices
    return prices / prices.iloc[0] - 1.0


def period_return(prices: pd.Series) -> float:
    if len(prices) < 2:
        return 0.0
    return float(prices.iloc[-1] / prices.iloc[0] - 1.0)


def cagr(prices: pd.Series) -> float:
    if len(prices) < 2:
        return 0.0
    total = prices.iloc[-1] / prices.iloc[0]
    days = (prices.index[-1] - prices.index[0]).days
    if days <= 0:
        return 0.0
    years = days / 365.25
    return float(total ** (1 / years) - 1.0)


def max_drawdown(prices: pd.Series) -> float:
    if prices.empty:
        return 0.0
    running_max = prices.cummax()
    dd = prices / running_max - 1.0
    return float(dd.min())


def volatility(prices: pd.Series, annualized: bool = True) -> float:
    rets = daily_returns(prices)
    if rets.empty:
        return 0.0
    vol = float(rets.std())
    return vol * np.sqrt(TRADING_DAYS) if annualized else vol


def sharpe_ratio(prices: pd.Series, risk_free: float = 0.03) -> float:
    rets = daily_returns(prices)
    if rets.empty or rets.std() == 0:
        return 0.0
    excess = rets - risk_free / TRADING_DAYS
    return float(excess.mean() / rets.std() * np.sqrt(TRADING_DAYS))


def summary_metrics(prices: pd.Series, risk_free: float = 0.03) -> dict:
    return {
        "total_return": period_return(prices),
        "cagr": cagr(prices),
        "volatility": volatility(prices),
        "max_drawdown": max_drawdown(prices),
        "sharpe": sharpe_ratio(prices, risk_free),
    }
