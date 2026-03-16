"""Global configuration for Turbogenius stock analyzer."""

# Supported markets
MARKETS = {
    "KOSPI": "KOSPI",
    "KOSDAQ": "KOSDAQ",
}

# yfinance ticker suffix by market
TICKER_SUFFIX = {
    "KOSPI": ".KS",
    "KOSDAQ": ".KQ",
}

# Available analysis periods
PERIODS = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
}

# Moving average windows (Korean market convention)
MA_WINDOWS = [5, 20, 60, 120]

MA_COLORS = {
    5: "#FF9500",
    20: "#007AFF",
    60: "#34C759",
    120: "#AF52DE",
}

# RSI settings
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Band settings
BB_PERIOD = 20
BB_STD = 2

# Korean market colors (red = up, blue = down)
COLOR_UP = "#FF3B30"
COLOR_DOWN = "#007AFF"

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-6"
