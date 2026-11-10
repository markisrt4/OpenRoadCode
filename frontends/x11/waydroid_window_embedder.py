# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compatibility import for the Waydroid platform adapter.

Process queries and output-settling workers belong to the application adapter
layer, rather than frontend presentation modules.
"""
from apps.orcUi.adapters.waydroid_window_embedder import WaydroidWindowEmbedder

__all__ = ['WaydroidWindowEmbedder']
