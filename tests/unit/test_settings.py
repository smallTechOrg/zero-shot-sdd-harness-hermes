from src.config.settings import get_settings


def test_no_key_resolves_to_stub(no_keys):
 s = get_settings()
 assert s.resolve_provider() == "stub"
 assert s.resolve_model() == ""


def test_auto_detects_anthropic(no_keys, monkeypatch):
 monkeypatch.setenv("AGENT_ANTHROPIC_API_KEY", "test-key-not-real")
 s = get_settings()
 assert s.resolve_provider() == "anthropic"
 assert s.resolve_model() == "claude-sonnet-4-6"


def test_auto_detects_nvidia_nim(no_keys, monkeypatch):
 monkeypatch.setenv("AGENT_OPENAI_API_KEY", "test-key-not-real")
 monkeypatch.setenv("AGENT_OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
 s = get_settings()
 assert s.resolve_provider() == "nim"
 assert s.resolve_model() == "meta/llama-3-8b-instruct"


def test_explicit_provider_and_model_win(no_keys, monkeypatch):
 monkeypatch.setenv("AGENT_LLM_PROVIDER", "gemini")
 monkeypatch.setenv("AGENT_LLM_MODEL", "gemini-2.5-flash")
 monkeypatch.setenv("AGENT_GEMINI_API_KEY", "test-key-not-real")
 s = get_settings()
 assert s.resolve_provider() == "gemini"
 assert s.resolve_model() == "gemini-2.5-flash"


def test_database_url_isolated_by_fixture(tmp_path):
 # conftest points every test at a tmp sqlite file
 assert get_settings().database_url.startswith("sqlite:///")
 assert "test.db" in get_settings().database_url
