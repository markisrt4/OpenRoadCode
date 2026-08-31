#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Install games used by the OpenRoadCode games launcher on Termux/X11.
# Missing packages are reported rather than making the whole setup fail.

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"

log() { printf '[orc-games] %s\n' "$*"; }
have_package() { apt-cache show "$1" >/dev/null 2>&1; }

install_if_available() {
    local package="$1"
    local binary="${2:-$1}"
    shift 2 || true
    local dependencies=("$@")
    if ! have_package "$package"; then
        log "not available in current Termux repositories: $package"
        UNAVAILABLE+=("$package")
        return 0
    fi
    for dependency in "${dependencies[@]}"; do
        if ! have_package "$dependency"; then
            log "dependency unavailable for $package: $dependency"
            UNAVAILABLE+=("$package")
            return 0
        fi
    done
    if command -v "$binary" >/dev/null 2>&1 && ((${#dependencies[@]} == 0)); then
        log "already installed: $package ($binary)"
        INSTALLED+=("$package")
        return 0
    fi
    log "installing: $package ${dependencies[*]}"
    pkg install -y "$package" "${dependencies[@]}"
    if command -v "$binary" >/dev/null 2>&1; then
        INSTALLED+=("$package")
    else
        log "installed $package, but expected binary '$binary' was not found"
        WARNINGS+=("$package")
    fi
}

if ! command -v pkg >/dev/null 2>&1; then
    echo 'This installer must be run inside Termux.' >&2
    exit 1
fi

log 'enabling Termux X11 repository'
pkg install -y x11-repo
log 'refreshing package metadata'
pkg update -y
log 'installing X11 embedding helper'
pkg install -y xdotool

INSTALLED=()
UNAVAILABLE=()
WARNINGS=()

install_if_available extremetuxracer extremetuxracer
install_if_available supertuxkart supertuxkart
install_if_available bovo bovo
install_if_available kmines kmines qt6-qtsvg
install_if_available kpat kpat
install_if_available gnome-2048 gnome-2048
install_if_available gnome-nibbles gnome-nibbles
install_if_available gnome-sudoku gnome-sudoku

printf '\n'
log 'installation summary'
if ((${#INSTALLED[@]})); then printf '  installed/ready:\n'; printf '    %s\n' "${INSTALLED[@]}"; else printf '  installed/ready: none\n'; fi
if ((${#UNAVAILABLE[@]})); then printf '  unavailable from configured Termux repos:\n'; printf '    %s\n' "${UNAVAILABLE[@]}"; fi
if ((${#WARNINGS[@]})); then printf '  installed but executable was not detected:\n'; printf '    %s\n' "${WARNINGS[@]}"; fi
printf '\n'
log 'detected ORC game executables:'
found_any=0
for binary in extremetuxracer supertuxkart bovo kmines kpat gnome-2048 gnome-nibbles gnome-sudoku; do
    if path="$(command -v "$binary" 2>/dev/null)"; then printf '  %-18s %s\n' "$binary" "$path"; found_any=1; fi
done
if ((found_any == 0)); then printf '  none\n'; fi
