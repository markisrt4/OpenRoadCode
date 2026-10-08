# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.poi.business_provider_catalog import get_business_provider


def test_panera_integration_loads_from_toml() -> None:
    provider = get_business_provider("panera")
    assert provider is not None
    assert provider.android_package == "com.panera.bread"
    assert provider.order_url is not None
    assert "panerabread.com" in provider.order_url
