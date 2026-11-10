# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def packages(feature):
    result = subprocess.run(["bash", "-c", 'source "$1"; get_feature_python_packages "$2"',
                             "feature-test", str(ROOT / "scripts/installers/installer_features.sh"), feature],
                            check=True, capture_output=True, text=True)
    return result.stdout.split()


def test_development_feature_provides_required_quality_tools():
    assert packages("development") == ["pytest", "ruff", "mypy==1.19.1"]


def test_runtime_base_keeps_development_tools_optional():
    assert not {"pytest", "ruff", "mypy==1.19.1"}.intersection(packages("base"))


def test_pinned_package_is_reinstalled_only_when_version_differs():
    source = (ROOT / "scripts/installers/install_python_env.sh").read_text()
    start = source.index("missing_python_packages=()")
    end = source.index("if (( ${#missing_python_packages[@]}", start)
    check = source[start:end]
    shell = '''
quality_version="$1"
python() {
  [[ "$4" == mypy && -n "$quality_version" ]] || return 1
  printf 'Name: mypy\\nVersion: %s\\n' "$quality_version"
}
unique_packages=('mypy==1.19.1')
''' + check + '''
printf '%s\\n' "${missing_python_packages[@]}"
'''
    for version, expected in (("1.19.1", False), ("1.18.0", True), ("", True)):
        result = subprocess.run(["bash", "-c", shell, "package-test", version],
                                check=True, capture_output=True, text=True)
        assert ("mypy==1.19.1" in result.stdout.splitlines()) is expected
