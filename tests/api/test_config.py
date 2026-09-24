from pathlib import Path

import pytest

from ai_os.api import ApiConfig


def test_api_configuration_is_loopback_only(tmp_path: Path) -> None:
    assert ApiConfig(root=tmp_path).host == "127.0.0.1"
    with pytest.raises(ValueError, match="loopback"):
        ApiConfig(root=tmp_path, host="0.0.0.0")
    with pytest.raises(ValueError, match="literal IP"):
        ApiConfig(root=tmp_path, host="localhost")


def test_api_configuration_bounds_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="page size"):
        ApiConfig(root=tmp_path, max_page_size=0)
    with pytest.raises(ValueError, match="request bound"):
        ApiConfig(root=tmp_path, max_request_bytes=10)
    with pytest.raises(ValueError, match="schema version"):
        ApiConfig(root=tmp_path, schema_version=2)
