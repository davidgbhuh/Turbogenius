"""Technical indicator calculations using pure pandas/numpy."""

import pandas as pd
import numpy as np
from config import MA_WINDOWS, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL, BB_PERIOD, BB_STD


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for window in MA_WINDOWS:
        result[f"MA{window}"] = result["Close"].rolling(window=window).mean()
    return result


def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    delta = result["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
    avg_loss = loss.ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result["RSI"] = 100 - (100 / (1 + rs))
    return result


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    ema_fast = result["Close"].ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = result["Close"].ewm(span=MACD_SLOW, adjust=False).mean()
    result["MACD"] = ema_fast - ema_slow
    result["MACD_signal"] = result["MACD"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    result["MACD_hist"] = result["MACD"] - result["MACD_signal"]
    return result


def add_bollinger(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    mid = result["Close"].rolling(window=BB_PERIOD).mean()
    std = result["Close"].rolling(window=BB_PERIOD).std()
    result["BB_mid"] = mid
    result["BB_upper"] = mid + BB_STD * std
    result["BB_lower"] = mid - BB_STD * std
    return result


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger(df)
    return df


def get_indicator_summary(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    summary = {
        "close": last["Close"],
        "volume": last["Volume"],
    }
    for window in MA_WINDOWS:
        col = f"MA{window}"
        if col in df.columns:
            summary[col] = last[col]
    for col in ["RSI", "MACD", "MACD_signal", "MACD_hist", "BB_upper", "BB_mid", "BB_lower"]:
        if col in df.columns:
            summary[col] = last[col]
    return summary
