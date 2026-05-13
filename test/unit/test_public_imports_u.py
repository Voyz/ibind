from setuptools import find_packages


def test_public_v2_imports_and_package_discovery():
    import ibind

    packages = find_packages()

    assert 'ibind.ws_v2' in packages
    assert 'ibind.ibkr_ws_v2' in packages
    assert ibind.IbkrWsClientV2 is not None
    assert ibind.events.WsOpen is not None
    assert ibind.subscriptions.MarketDataSubscription is not None
