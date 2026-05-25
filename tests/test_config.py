import os
import tempfile
import pytest
from pathlib import Path

from token_usage.config import default_config_path, load_config


def test_load_config_from_yaml():
    yaml_content = """
opencode:
  workspace_id: "wrk_test"
  auth_cookie: "test_cookie"
deepseek:
  api_key: "sk-test"
refresh_interval: 60
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = load_config(f.name)

    assert config["opencode"]["workspace_id"] == "wrk_test"
    assert config["opencode"]["auth_cookie"] == "test_cookie"
    assert config["deepseek"]["api_key"] == "sk-test"
    assert config["refresh_interval"] == 60
    os.unlink(f.name)


def test_load_config_missing_file():
    config = load_config("/nonexistent/path/config.yaml")
    assert config == {"refresh_interval": 300}


def test_load_config_empty_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        f.flush()
        config = load_config(f.name)

    assert config == {"refresh_interval": 300}
    os.unlink(f.name)


def test_load_config_env_override(monkeypatch, tmp_path):
    yaml_content = """
deepseek:
  api_key: "from_yaml"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content)

    monkeypatch.setenv("TOKEN_USAGE_OPENAI_ACCESS_TOKEN", "from_env")

    config = load_config(str(config_file))
    assert config["deepseek"]["api_key"] == "from_yaml"
    assert config["openai"]["access_token"] == "from_env"


def test_load_config_uses_env_config_path(monkeypatch, tmp_path):
    config_file = tmp_path / "custom.yaml"
    config_file.write_text("refresh_interval: 42\n", encoding="utf-8")

    monkeypatch.setenv("TOKEN_USAGE_CONFIG", str(config_file))

    config = load_config()
    assert config["refresh_interval"] == 42


def test_default_config_path_uses_appdata_on_windows(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\Tester\AppData\Roaming")

    assert default_config_path() == (
        Path(r"C:\Users\Tester\AppData\Roaming") / "token-usage" / "config.yaml"
    )


def test_default_config_path_uses_xdg_style_on_non_windows(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("HOME", "/home/tester")

    assert default_config_path() == Path("/home/tester/.config/token-usage/config.yaml")


def test_load_config_partial_platforms():
    yaml_content = """
zhipu:
  api_key: "zhipu_key"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = load_config(f.name)

    assert "zhipu" in config
    assert "opencode" not in config
    os.unlink(f.name)
