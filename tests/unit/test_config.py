from config import DEFAULT_CONFIG


def test_default_runtime_flags_match_current_latency_strategy():
    assert DEFAULT_CONFIG.enable_thinking is False
    assert DEFAULT_CONFIG.history_window == 4
