"""Minimal smoke tests so CI pytest does not exit 5 (no tests collected)."""


def test_import_plugin():
    from ape_flashbots.providers import FlashbotsConfig, FlashbotsProvider

    assert FlashbotsProvider is not None
    assert FlashbotsConfig is not None
