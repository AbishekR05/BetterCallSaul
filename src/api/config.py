# src/api/config.py
"""
API Configuration Settings Loader (§4).
Loads non-secret settings from configs/p30_api.yaml and environment variables.
"""

import os
import yaml
from typing import List, Dict, Any


class APISettings:
    """Settings container for Phase 3.0 API."""

    def __init__(self, config_path: str = "configs/p30_api.yaml"):
        self.config_path = config_path
        self.host: str = "0.0.0.0"
        self.port: int = 8000
        self.log_level: str = "INFO"
        self.request_size_limit_bytes: int = 102400
        self.cors_allowed_origins: List[str] = ["*"]
        self.login_max_attempts: int = 5
        self.rate_limit_window_minutes: int = 15

        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                api_cfg = data.get("api", {})
                cors_cfg = data.get("cors", {})
                rate_cfg = data.get("rate_limit", {})

                self.host = api_cfg.get("host", self.host)
                self.port = int(api_cfg.get("port", self.port))
                self.log_level = api_cfg.get("log_level", self.log_level)
                self.request_size_limit_bytes = int(api_cfg.get("request_size_limit_bytes", self.request_size_limit_bytes))

                self.cors_allowed_origins = cors_cfg.get("allowed_origins", self.cors_allowed_origins)

                self.login_max_attempts = int(rate_cfg.get("login_max_attempts", self.login_max_attempts))
                self.rate_limit_window_minutes = int(rate_cfg.get("window_minutes", self.rate_limit_window_minutes))
            except Exception as e:
                print(f"[APISettings Warning] Failed to parse '{self.config_path}': {e}")


def get_api_settings() -> APISettings:
    """Returns singleton APISettings instance."""
    return APISettings()
