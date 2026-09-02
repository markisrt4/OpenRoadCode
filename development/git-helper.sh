#!/usr/bin/env bash
# Interactive Git helper for OpenRoadCode.
#
# Walks through changed/untracked files one at a time, stages the selected
# files, creates a commit message from the staged paths, commits, and then
# optionally pushes the current branch.

set -u

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: this command must be run inside a Git repository." >&2
    exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root" || exit 1

current_branch="$(git branch --show-current)"
if [[ -z "$current_branch" ]]; then
    echo "Error: detached HEAD. Check out a branch before using this helper." >&2
    exit 1
fi

echo "Repository: $(basename "$repo_root")"
echo "Branch:     $current_branch"
echo

# Keep anything the user had already staged. Only prompt for unstaged and
# untracked paths, so running this helper never silently unstages prior work.
mapfile -d '' changed_files < <(
    {
        git diff --name-only -z
        git ls-files --others --exclude-standard -z
    } | awk -v RS='\0' -v ORS='\0' '!seen[$0]++'
)

if (( ${#changed_files[@]} == 0 )); then
    if git diff --cached --quiet; then
        echo "Nothing to stage or commit. The repository is clean. Suspiciously responsible."
        exit 0
    fi
    echo "No unstaged changes. Using files that are already staged."
else
    echo "Choose which changed files to stage:"
    echo

    for file in "${changed_files[@]}"; do
        status="$(git status --short -- "$file" | head -n 1)"
        printf '%s\n' "$status"

        while true; do
            read -r -p "Stage '$file'? [y/N/q] " answer
            case "${answer,,}" in
                y|yes)
                    git add -A -- "$file"
                    echo "  staged"
                    break
                    ;;
                q|quit)
                    echo "Aborted. Files staged so far remain staged."
                    exit 0
                    ;;
                n|no|"")
                    echo "  skipped"
                    break
                    ;;
                *)
                    echo "Please answer y, n, or q. Humanity has invented enough ambiguous interfaces."
                    ;;
            esac
        done
        echo
    done
fi

if git diff --cached --quiet; then
    echo "No files are staged. Nothing to commit."
    exit 0
fi

echo "Staged changes:"
git diff --cached --stat
echo

# Generate a compact commit subject from the staged paths. Prefer the first
# common top-level area when all changes live together; otherwise summarize
# the first few file names.
mapfile -t staged_files < <(git diff --cached --name-only)

if (( ${#staged_files[@]} == 1 )); then
    file="${staged_files[0]}"
    base="$(basename "$file")"

    if git diff --cached --diff-filter=A --name-only -- "$file" | grep -q .; then
        commit_message="Add $base"
    elif git diff --cached --diff-filter=D --name-only -- "$file" | grep -q .; then
        commit_message="Remove $base"
    else
        commit_message="Update $base"
    fi
else
    first_top="${staged_files[0]%%/*}"
    same_top=true
    for file in "${staged_files[@]}"; do
        if [[ "${file%%/*}" != "$first_top" ]]; then
            same_top=false
            break
        fi
    done

    if [[ "$same_top" == true && "${staged_files[0]}" == */* ]]; then
        commit_message="Update $first_top"
    else
        commit_message="Update ${#staged_files[@]} files"
    fi
fi

echo "Generated commit message:"
echo "  $commit_message"
echo

if ! git commit -m "$commit_message"; then
    echo "Commit failed. Nothing was pushed." >&2
    exit 1
fi

echo
while true; do
    read -r -p "Push '$current_branch' now? [y/N] " answer
    case "${answer,,}" in
        y|yes)
            if git push; then
                echo "Push complete."
            else
                echo "Push failed. The commit is still safely stored locally." >&2
                exit 1
            fi
            break
            ;;
        n|no|"")
            echo "Not pushed. Commit remains local."
            break
            ;;
        *)
            echo "Please answer y or n."
            ;;
    esac
done
