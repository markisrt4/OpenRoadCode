# SPDX-License-Identifier: MIT

"""Toolkit-independent marker for presentation objects covered by UI policy."""


class UiWidget:
    """Opt in to the repository's presentation dependency policy.

    Implementations present supplied state and emit semantic requests through
    toolkit-independent contracts. Composition constructs and injects concrete
    dependencies; widgets do not resolve services, construct backends, or inspect
    another object's private state. Toolkit-specific rendering stays local.

    This marker provides no constructor, lifecycle, registration, or dependency
    injection machinery. The architecture gate checks marked modules, including
    subclasses outside the usual frontend directories. Existing directory checks
    remain mandatory even for unmarked widgets.
    """

    __slots__ = ()
