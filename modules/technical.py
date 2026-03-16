"""Technical indicator calculations using pandas-ta."""

import pandas as pd
import pandas_ta as ta
from config import MA_WINDOWS, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL, BB_PERIOD, BB_STD


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Add MA columns (MA5, MA20, MA60, MA120) to the DataFrame."""
    result = df.copy()
    for window in MA_WINDOWS:
        result[f"MA{window}"] = ta.sma(result["Close"], length=window)
    return result


def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Add RSI column to the DataFrame."""
    result = df.copy()
    result["RSI"] = ta.rsi(result["Close"], length=RSI_PERIOD)
    return result


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Add MACD, MACD_signal, MACD_hist columns to the DataFrame."""
    result = df.copy()
    macd_df = ta.macd(result["Close"], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    if macd_df is not None and not macd_df.empty:
        result["MACD"] = macd_df.iloc[:, 0]
        result["MACD_signal"] = macd_df.iloc[:, 1]
        result["MACD_hist"] = macd_df.iloc[:, 2]
    return result


def add_bollinger(df: pd.DataFrame) -> pd.DataFrame:
    """Add BB_upper, BB_mid, BB_lower columns to the DataFrame."""
    result = df.copy()
    bb_df = ta.bbands(result["Close"], length=BB_PERIOD, std=BB_STD)
    if bb_df is not None and not bb_df.empty:
        result["BB_lower"] = bb_df.iloc[:, 0]
        result["BB_mid"] = bb_df.iloc[:, 1]
        result["BB_upper"] = bb_df.iloc[:, 2]
    return result


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators in one call."""
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger(df)
    return df


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """Return the latest values of all indicators as a dict."""
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
