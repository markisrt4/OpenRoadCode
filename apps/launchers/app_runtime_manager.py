# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility import for the relocated application runtime controller.

New code should import ``controllers.application_runtime.AppRuntimeManager``.
This shim remains temporarily so downstream branches do not break during the
runtime-integration cleanup.
"""

from controllers.application_runtime import AppRuntimeManager, ManagedApplication

__all__ = ["AppRuntimeManager", "ManagedApplication"]
