"""Minimal smoke tests so CI pytest does not exit 5 (no tests collected)."""


def test_import_plugin():
    from ape_flashbots import providers as flashbots_providers

    assert flashbots_providers.FlashbotsProvider is not None
    assert flashbots_providers.FlashbotsConfig is not None
