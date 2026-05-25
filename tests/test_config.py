import os
import tempfile
import pytest
from token_usage.config import load_config


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
