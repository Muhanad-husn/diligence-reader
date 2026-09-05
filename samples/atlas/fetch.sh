#!/usr/bin/env bash
# Sparse-checks out `data_room/` alone from the public `synthetic-dataRoom` repository, at
# a pinned commit, and asserts nothing else landed on the runner [#71].
#
# The corpus this project reads (docs/corpus.md) lives inside a larger upstream repository
# that also holds `evaluator_private/`, `generator/`, `FINAL_AGENT_SCORING_VERDICT.md` and
# four `data_room_*` directories holding the author's own solved runs — exactly the
# material `sandbox-guard` refuses to read locally, because reading it before the schema
# and queries are written would defeat this project's central claim. A plain `git clone`
# of the upstream repository puts all of that on the runner. This script instead:
#
#   - sparse-checks out the one path that matters, in non-cone mode. Cone mode always checks
#     out top-level files regardless of the pattern given, and `FINAL_AGENT_SCORING_VERDICT.md`
#     sits at the repository root — cone mode would put it on the runner by construction.
#   - fetches with `--filter=blob:none`, a partial clone: file *content* outside the sparse
#     pattern is never transferred, only the tree and commit metadata needed to resolve it.
#   - is pinned to a commit SHA (docs/corpus.md), not a branch, so the corpus a run reads
#     cannot move under it. Cost and blast radius under a lost or misapplied sparse pattern
#     are bounded by `--filter=blob:none`: content outside the pattern is never fetched.
#     That bound holds only because the pattern held in the first place — it is not a
#     second, independent wall behind the assertions below.
#   - asserts the result, rather than trusting the sparse pattern: it fails loudly if
#     anything besides `data_room/` shows up, and it deletes its own scratch clone (`$work`)
#     the moment the copy is made, so no git metadata that could reach the sealed material
#     lingers on disk afterwards. `assert_only_data_room` only inspects the two known path
#     components (`synthetic_vdr_project_atlas`, then `data_room`) and stops there, so
#     sealed material planted *inside* `data_room/` itself upstream, under a name that is
#     not on the list above, is invisible to it — the sparse pattern would happily fetch
#     it, and only `assert_no_forbidden_names` would catch it, by walking the whole tree.
#     The tree-identity check in `fetch()` is the backstop for a name that is on neither:
#     it compares the whole subtree's tree SHA against the one pinned in docs/corpus.md, so
#     any change to what is inside `data_room/` fails the fetch. That check is a tripwire
#     against drift under a fixed pin, not a review of content — re-pinning it to a new
#     commit re-arms it around whatever is at that commit, sight unseen.
#
# Usage:
#   fetch-corpus.sh <dest-dir>
#     Fetches $CORPUS_COMMIT (required env var) into <dest-dir>, replacing it entirely.
#   fetch-corpus.sh --check-firewall <dir>
#     Runs both firewall assertions — the named list and the structural check — against an
#     existing directory tree, no network. This is the seam tests/test_ci_corpus_fetch.py
#     drives directly; the fetch itself is exercised end to end in the same test file
#     against a local fixture repository, also without network.

set -euo pipefail

CORPUS_REPO="${CORPUS_REPO:-https://github.com/brainqub3/synthetic-dataRoom}"
CORPUS_SUBDIR="synthetic_vdr_project_atlas/data_room"
# CLAUDE.md's sealed material is four things, not three: the ontology, the rubric and
# answer key, the scoring verdict, and "the four data_room_* directories holding the
# author's own solved runs". "data_room_*" (not "data_room", which has no trailing
# underscore) names that fourth thing without hard-coding all four directory names.
FORBIDDEN_NAMES=("evaluator_private" "generator" "FINAL_AGENT_SCORING_VERDICT.md" "data_room_*")

# Fails loudly, naming what it found, if any of FORBIDDEN_NAMES appears anywhere under $1.
assert_no_forbidden_names() {
    local dir="$1"
    local name hit
    for name in "${FORBIDDEN_NAMES[@]}"; do
        hit=$(find "$dir" -path "*/.git" -prune -o -name "$name" -print)
        if [[ -n "$hit" ]]; then
            echo "FIREWALL BREACH: '$name' landed on the runner at:" >&2
            echo "$hit" >&2
            echo "Refusing to proceed. Nothing outside data_room/ may reach this machine." >&2
            return 1
        fi
    done
    return 0
}

# The structural check: the fetch root must hold nothing but $CORPUS_SUBDIR, and nothing
# else at any level in between. This catches anything the named-forbidden-list above does
# not, including a directory added upstream after this script was written. Walks
# CORPUS_SUBDIR one path component at a time rather than assuming it is exactly two
# components deep.
assert_only_data_room() {
    local root="$1"
    local current="$root"
    local parts component listing

    IFS='/' read -ra parts <<<"$CORPUS_SUBDIR"
    for component in "${parts[@]}"; do
        listing=$(find "$current" -mindepth 1 -maxdepth 1 -not -name .git)
        if [[ "$listing" != "$current/$component" ]]; then
            echo "FIREWALL BREACH: expected only '$component' under $current, found:" >&2
            echo "$listing" >&2
            return 1
        fi
        current="$current/$component"
    done
    return 0
}

fetch() {
    local dest="${1:?usage: fetch-corpus.sh <dest-dir>}"
    local commit="${CORPUS_COMMIT:?CORPUS_COMMIT must be set to a pinned commit SHA (docs/corpus.md)}"
    local expected_tree="${CORPUS_TREE_SHA:?CORPUS_TREE_SHA must be set to the pinned tree SHA for $CORPUS_SUBDIR (docs/corpus.md)}"

    local work
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT

    git -C "$work" init -q
    git -C "$work" remote add origin "$CORPUS_REPO"
    git -C "$work" sparse-checkout set --no-cone "$CORPUS_SUBDIR/*"
    git -C "$work" fetch --filter=blob:none --depth 1 origin "$commit"
    git -C "$work" checkout -q FETCH_HEAD

    assert_no_forbidden_names "$work"
    assert_only_data_room "$work"

    local fetched="$work/$CORPUS_SUBDIR"
    if [[ ! -d "$fetched" ]]; then
        echo "fetch-corpus: expected $CORPUS_SUBDIR at commit $commit, found nothing" >&2
        exit 1
    fi

    # Tree identity, not a file count. A count is fixed by construction at a pinned commit
    # and a fixed pattern, so there is nothing about the pin left for it to catch; a rename,
    # a move within the subtree, or any other same-count content swap passes it silently.
    # Comparing the subtree's own tree object against the SHA pinned in docs/corpus.md
    # catches all of those, and is the anchor for the corpus-identity claim that
    # docs/corpus.md and the acceptance-suite transcripts otherwise rest on file count alone.
    local tree_sha
    tree_sha=$(git -C "$work" rev-parse "FETCH_HEAD:$CORPUS_SUBDIR")
    if [[ "$tree_sha" != "$expected_tree" ]]; then
        echo "fetch-corpus: expected tree $expected_tree at $CORPUS_SUBDIR (docs/corpus.md)," \
            "found $tree_sha — content under the pin does not match" >&2
        exit 1
    fi

    rm -rf "$dest"
    mkdir -p "$(dirname "$dest")"
    cp -r "$fetched" "$dest"
    rm -rf "$work"
    trap - EXIT

    local count
    count=$(find "$dest" -type f | wc -l)
    echo "fetch-corpus: $count files installed to $dest at commit $commit (tree $tree_sha)"
}

main() {
    if [[ "${1:-}" == "--check-firewall" ]]; then
        local dir="${2:?usage: fetch-corpus.sh --check-firewall <dir>}"
        assert_no_forbidden_names "$dir" || return 1
        assert_only_data_room "$dir" || return 1
        return 0
    fi

    fetch "$@"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
