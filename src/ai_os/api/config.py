"""Fail-closed Runtime API configuration."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path

from ai_os.config import EnvironmentProfile


@dataclass(frozen=True)
class ApiConfig:
    root: Path
    host: str = "127.0.0.1"
    port: int = 8765
    environment: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT
    max_page_size: int = 100
    max_request_bytes: int = 65_536
    max_dry_run_steps: int = 64
    max_audit_events: int = 1_000
    request_timeout_seconds: float = 5.0
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported API configuration schema version")
        if not self.root.is_dir():
            raise ValueError("API root must be an existing directory")
        try:
            address = ip_address(self.host)
        except ValueError as error:
            raise ValueError("API host must be a literal IP address") from error
        if not address.is_loopback:
            raise ValueError("Runtime API must bind to a loopback address")
        if not 1 <= self.port <= 65_535:
            raise ValueError("API port must be within 1..65535")
        if not 1 <= self.max_page_size <= 1_000:
            raise ValueError("API page size must be within 1..1000")
        if not 1_024 <= self.max_request_bytes <= 1_048_576:
            raise ValueError("API request bound must be within 1024..1048576 bytes")
        if not 1 <= self.max_dry_run_steps <= 256:
            raise ValueError("API dry-run step bound must be within 1..256")
        if not 1 <= self.max_audit_events <= 10_000:
            raise ValueError("API audit bound must be within 1..10000")
        if not 0 < self.request_timeout_seconds <= 30:
            raise ValueError("API timeout must be within thirty seconds")
