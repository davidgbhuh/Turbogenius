"""GitHub API를 통한 ETF 포트폴리오 이력 영구 저장."""

import base64
import json
import requests
import streamlit as st

_API = "https://api.github.com"
_REPO = "davidgbhuh/Turbogenius"
_FILE = "data/etf_portfolio_history.json"
_BRANCH = "claude/etf-portfolio-dashboard-NsTvw"


def _token() -> str:
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return ""


def _headers() -> dict:
    return {
        "Authorization": f"token {_token()}",
        "Accept": "application/vnd.github.v3+json",
    }


def load_from_github() -> tuple[list, str | None]:
    """GitHub에서 이력 파일을 읽습니다.

    Returns:
        (history_list, sha) — 파일이 없거나 토큰 미설정 시 ([], None)
    """
    if not _token():
        return [], None
    try:
        url = f"{_API}/repos/{_REPO}/contents/{_FILE}?ref={_BRANCH}"
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code == 404:
            return [], None
        if resp.status_code == 200:
            data = resp.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(content), data["sha"]
    except Exception:
        pass
    return [], None


def save_to_github(history: list, sha: str | None) -> str | None:
    """GitHub에 이력 파일을 저장(생성/업데이트)합니다.

    Args:
        history: 저장할 이력 리스트.
        sha: 기존 파일의 SHA (없으면 None → 신규 생성).

    Returns:
        업데이트된 파일 SHA, 실패 시 None.
    """
    if not _token():
        return None
    try:
        content_b64 = base64.b64encode(
            json.dumps(history, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")

        body: dict = {
            "message": "chore: ETF 포트폴리오 이력 자동 저장",
            "content": content_b64,
            "branch": _BRANCH,
        }
        if sha:
            body["sha"] = sha

        url = f"{_API}/repos/{_REPO}/contents/{_FILE}"
        resp = requests.put(url, headers=_headers(), json=body, timeout=15)
        if resp.status_code in (200, 201):
            return resp.json()["content"]["sha"]
    except Exception:
        pass
    return None


def is_configured() -> bool:
    """GitHub Token이 설정되어 있으면 True."""
    return bool(_token())
