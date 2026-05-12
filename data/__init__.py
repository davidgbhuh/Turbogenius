"""정적 데이터 패키지 — ETF 리스트(csv) 및 분기별 모델 포트폴리오(py)."""
from .portfolios import (
    NOTES,
    PROFILE_SUMMARY,
    QUARTERLY_MODELS,
    RISK_PROFILES,
    Quarter,
    current_quarter,
    get_model,
    get_note,
    list_quarters,
    validate_all,
)

__all__ = [
    "NOTES",
    "PROFILE_SUMMARY",
    "QUARTERLY_MODELS",
    "RISK_PROFILES",
    "Quarter",
    "current_quarter",
    "get_model",
    "get_note",
    "list_quarters",
    "validate_all",
]
