# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Lifecycle policy for externally launched applications."""

from .app_runtime_manager import AppRuntimeManager, ManagedApplication

__all__ = ["AppRuntimeManager", "ManagedApplication"]
