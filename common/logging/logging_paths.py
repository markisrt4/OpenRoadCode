from __future__ import annotations

import os
from pathlib import Path


def logging_tmp_dir(app_name: str) -> Path:
    """Return the temporary logging directory for an application.

    The directory is resolved in the following order:

    1. LOGGING_TMP_DIR
    2. TMPDIR
    3. ~/.cache/<app_name>/tmp

    The directory is created if it does not already exist.

    @param app_name Non-empty application name used by the fallback path.
    @return Existing, writable logging directory.
    @raises ValueError if ``app_name`` is empty.
    @raises OSError if the directory cannot be created.
    """
    if not app_name:
        raise ValueError("app_name cannot be empty")

    tmp_dir = Path(
        os.getenv(
            "LOGGING_TMP_DIR",
            os.getenv(
                "TMPDIR",
                str(
                    Path.home()
                    / ".cache"
                    / app_name
                    / "tmp"
                ),
            ),
        )
    )

    tmp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return tmp_dir


def logging_file_path(
    app_name: str,
    name: str,
) -> Path:
    """Return a path within an application's temporary logging directory.

    @param app_name Non-empty application name used to select the directory.
    @param name Non-empty log filename.
    @return Path below `logging_tmp_dir(app_name)`; the file is not created.
    @raises ValueError if ``app_name`` or ``name`` is empty.
    """
    if not name:
        raise ValueError("name cannot be empty")

    return logging_tmp_dir(app_name) / name
