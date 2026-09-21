# src/api/config.py
"""
API Configuration Settings Loader (§4, §12).
Loads non-secret settings from configs/p31_hardening.yaml (or p30_api.yaml fallback) and environment variables.
Provides startup validation for production readiness.
"""

import os
import yaml
from typing import List, Dict, Any, Optional


class APISettings:
    """Settings container for Phase 3.1 Hardened API."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            if os.path.exists("configs/p31_hardening.yaml"):
                config_path = "configs/p31_hardening.yaml"
            else:
                config_path = "configs/p30_api.yaml"

        self.config_path = config_path

        # Core app environment & mode
        self.app_env: str = os.getenv("APP_ENV", "production").lower()
        self.debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
        self.docs_enabled: bool = os.getenv("APP_DOCS_ENABLED", "false").lower() == "true" if self.app_env == "production" else True

        self.host: str = os.getenv("API_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("API_PORT", "8000"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # Timeouts (seconds)
        self.request_timeout_s: float = 30.0
        self.turn_timeout_s: float = 60.0
        self.queue_wait_timeout_s: float = 10.0

        # Field & payload limits
        self.request_size_limit_bytes: int = 102400  # 100 KB
        self.auth_identifier_max_length: int = 254
        self.password_min_length: int = 8
        self.password_max_length: int = 128
        self.turn_query_max_length: int = 2000
        self.session_title_max_length: int = 200

        # Rate Limiting
        self.rate_limit_enabled: bool = True
        self.rate_limit_backend: str = "memory"  # memory | disabled
        self.rate_limit_rules: Dict[str, Dict[str, int]] = {
            "register_ip": {"requests": 5, "window_s": 3600},
            "login_ip": {"requests": 10, "window_s": 60},
            "login_identifier": {"requests": 5, "window_s": 900},
            "session_create_user": {"requests": 20, "window_s": 60},
            "turn_create_user": {"requests": 10, "window_s": 60},
            "session_read_delete_user": {"requests": 120, "window_s": 60},
        }

        # Concurrency
        self.max_concurrent_turns: int = 2
        self.session_serialization: bool = True

        # Security & Logging
        self.cors_allowed_origins: List[str] = ["https://app.bettercallsaul.local"]
        self.trusted_proxies: List[str] = []
        self.response_timing_header: bool = True
        self.access_log_exclude_paths: List[str] = ["/health", "/ready"]
        self.log_redaction_enabled: bool = True

        # Phase 3.0 backward compatibility properties
        self.login_max_attempts: int = 5
        self.rate_limit_window_minutes: int = 15

        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                if "app_env" in data:
                    self.app_env = data["app_env"].lower()
                if "debug" in data:
                    self.debug = bool(data["debug"])
                if "docs_enabled" in data:
                    self.docs_enabled = bool(data["docs_enabled"])

                timeouts = data.get("timeouts", {})
                self.request_timeout_s = float(timeouts.get("request_timeout_s", self.request_timeout_s))
                self.turn_timeout_s = float(timeouts.get("turn_timeout_s", self.turn_timeout_s))
                self.queue_wait_timeout_s = float(timeouts.get("queue_wait_timeout_s", self.queue_wait_timeout_s))

                limits = data.get("limits", {})
                self.request_size_limit_bytes = int(limits.get("max_request_size_bytes", self.request_size_limit_bytes))
                self.auth_identifier_max_length = int(limits.get("auth_identifier_max_length", self.auth_identifier_max_length))
                self.password_min_length = int(limits.get("password_min_length", self.password_min_length))
                self.password_max_length = int(limits.get("password_max_length", self.password_max_length))
                self.turn_query_max_length = int(limits.get("turn_query_max_length", self.turn_query_max_length))
                self.session_title_max_length = int(limits.get("session_title_max_length", self.session_title_max_length))

                rl_cfg = data.get("rate_limit", {})
                self.rate_limit_enabled = bool(rl_cfg.get("enabled", self.rate_limit_enabled))
                self.rate_limit_backend = str(rl_cfg.get("backend", self.rate_limit_backend))
                if "rules" in rl_cfg:
                    self.rate_limit_rules.update(rl_cfg["rules"])

                conc = data.get("concurrency", {})
                self.max_concurrent_turns = int(conc.get("max_concurrent_turns", self.max_concurrent_turns))
                self.session_serialization = bool(conc.get("session_serialization", self.session_serialization))

                sec = data.get("security", {})
                if "cors_allowed_origins" in sec:
                    self.cors_allowed_origins = list(sec["cors_allowed_origins"])
                if "trusted_proxies" in sec:
                    self.trusted_proxies = list(sec["trusted_proxies"])
                if "response_timing_header" in sec:
                    self.response_timing_header = bool(sec["response_timing_header"])
                if "access_log_exclude_paths" in sec:
                    self.access_log_exclude_paths = list(sec["access_log_exclude_paths"])
                if "log_redaction_enabled" in sec:
                    self.log_redaction_enabled = bool(sec["log_redaction_enabled"])

                # Legacy p30 fallback
                api_cfg = data.get("api", {})
                if api_cfg:
                    self.host = api_cfg.get("host", self.host)
                    self.port = int(api_cfg.get("port", self.port))
                    self.log_level = api_cfg.get("log_level", self.log_level)
                    if "request_size_limit_bytes" in api_cfg:
                        self.request_size_limit_bytes = int(api_cfg["request_size_limit_bytes"])

            except Exception as e:
                print(f"[APISettings Warning] Failed to parse '{self.config_path}': {e}")

    def validate(self):
        """Validate startup configuration; fail fast on invalid setting (§12)."""
        if self.request_timeout_s <= 0:
            raise ValueError("Configuration Error: request_timeout_s must be positive")
        if self.turn_timeout_s <= 0:
            raise ValueError("Configuration Error: turn_timeout_s must be positive")
        if self.queue_wait_timeout_s <= 0:
            raise ValueError("Configuration Error: queue_wait_timeout_s must be positive")
        if self.request_size_limit_bytes <= 0:
            raise ValueError("Configuration Error: max_request_size_bytes must be positive")
        if self.max_concurrent_turns <= 0:
            raise ValueError("Configuration Error: max_concurrent_turns must be positive")

        if self.app_env == "production":
            if "*" in self.cors_allowed_origins:
                raise ValueError("Configuration Error: cors_allowed_origins cannot contain wildcard '*' in production mode")
            if self.debug:
                raise ValueError("Configuration Error: debug mode cannot be enabled in production mode")
            if self.rate_limit_backend == "disabled" or not self.rate_limit_enabled:
                raise ValueError("Configuration Error: rate limiter cannot be disabled in production mode")


def get_api_settings() -> APISettings:
    """Returns singleton APISettings instance."""
    settings = APISettings()
    return settings

