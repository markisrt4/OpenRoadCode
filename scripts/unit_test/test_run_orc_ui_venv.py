"""Exercise launcher interpreter selection without provisioning Python."""

import os
import shutil
import subprocess
from pathlib import Path


def test_launcher_creates_missing_venv_and_reuses_it(tmp_path):
    launcher = tmp_path / "runOrcUi"
    shutil.copyfile(Path(__file__).resolve().parents[2] / "runOrcUi", launcher)
    tools = tmp_path / "tools"
    tools.mkdir()
    python = tools / "python3"
    python.write_text(
        "#!/bin/bash\n"
        "set -eu\n"
        '[[ "$1 $2 $3" == "-m venv --system-site-packages" ]]\n'
        'mkdir -p "$4/bin"\n'
        "printf '#!/bin/bash\\nexit 0\\n' > \"$4/bin/python\"\n"
        'chmod +x "$4/bin/python"\n'
    )
    python.chmod(0o755)
    env = {"PATH": f"{tools}{os.pathsep}{os.defpath}"}

    first = subprocess.run(["bash", str(launcher)], env=env, capture_output=True, check=True)
    assert b"Creating OpenRoadCode virtual environment" in first.stderr
    assert (tmp_path / ".venv/bin/python").is_file()

    second = subprocess.run(["bash", str(launcher)], env=env, capture_output=True, check=True)
    assert b"Creating OpenRoadCode virtual environment" not in second.stderr
