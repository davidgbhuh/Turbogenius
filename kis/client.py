"""KIS OpenAPI client — token management and base request layer."""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

REAL_HOST = "https://openapi.koreainvestment.com:9443"
MOCK_HOST = "https://openapivts.koreainvestment.com:29443"

TOKEN_CACHE_DIR = Path.home() / ".cache" / "turbogenius"
TOKEN_CACHE_FILE = TOKEN_CACHE_DIR / "kis_token.json"


class KISError(RuntimeError):
    pass


@dataclass
class _Token:
    access_token: str
    expires_at: float

    def valid(self) -> bool:
        return time.time() < self.expires_at - 60


class KISClient:
    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        env: str | None = None,
    ) -> None:
        self.app_key = app_key or os.getenv("KIS_APP_KEY", "")
        self.app_secret = app_secret or os.getenv("KIS_APP_SECRET", "")
        env = (env or os.getenv("KIS_ENV") or "real").lower()
        self.host = MOCK_HOST if env == "mock" else REAL_HOST
        self._token: _Token | None = None
        self._lock = threading.Lock()
        if not self.app_key or not self.app_secret:
            raise KISError(
                "KIS_APP_KEY / KIS_APP_SECRET 가 설정되지 않았습니다. .env 또는 환경변수를 확인하세요."
            )

    # --- token ---------------------------------------------------------
    def _load_cached_token(self) -> _Token | None:
        try:
            data = json.loads(TOKEN_CACHE_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        if data.get("app_key") != self.app_key or data.get("host") != self.host:
            return None
        tok = _Token(data["access_token"], float(data["expires_at"]))
        return tok if tok.valid() else None

    def _save_cached_token(self, tok: _Token) -> None:
        TOKEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_FILE.write_text(
            json.dumps(
                {
                    "app_key": self.app_key,
                    "host": self.host,
                    "access_token": tok.access_token,
                    "expires_at": tok.expires_at,
                }
            )
        )

    def _issue_token(self) -> _Token:
        url = f"{self.host}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        resp = requests.post(url, json=body, timeout=10)
        if resp.status_code != 200:
            raise KISError(f"토큰 발급 실패 ({resp.status_code}): {resp.text}")
        data = resp.json()
        if "access_token" not in data:
            raise KISError(f"토큰 발급 실패: {data}")
        expires_in = int(data.get("expires_in", 86400))
        tok = _Token(data["access_token"], time.time() + expires_in)
        self._save_cached_token(tok)
        return tok

    def access_token(self) -> str:
        with self._lock:
            if self._token and self._token.valid():
                return self._token.access_token
            cached = self._load_cached_token()
            if cached:
                self._token = cached
                return cached.access_token
            self._token = self._issue_token()
            return self._token.access_token

    # --- request -------------------------------------------------------
    def get(self, path: str, tr_id: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.host}{path}"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            raise KISError(f"KIS API {tr_id} 호출 실패 ({resp.status_code}): {resp.text}")
        data = resp.json()
        rt_cd = data.get("rt_cd")
        if rt_cd and rt_cd != "0":
            raise KISError(f"KIS API 응답 오류 [{rt_cd}] {data.get('msg1', '')}")
        return data
