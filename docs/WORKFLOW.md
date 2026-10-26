# Git workflow

This repository follows Git flow. The two permanent branches are:

| Branch | Purpose |
| --- | --- |
| `main` | Stable releases and the GitHub default branch |
| `develop` | Integration of changes for the next release |

`main` requires a pull request before merging, including for the repository
owner. Force pushes and branch deletion are blocked. An external approval is
not required, so a sole maintainer can merge their own pull requests. Resolve
review conversations before merging. Do not bypass or disable these protections
to publish a change.

## Features and fixes

Start ordinary work from an up-to-date `develop`:

```sh
git switch develop
git pull --ff-only
git switch -c feature/short-description
```

Commit on the feature branch, push it, and open a pull request targeting
`develop`. Use `fix/short-description` for ordinary bug fixes. Before merging,
run the relevant tests and the repository boundary check:

```sh
/usr/bin/python3 -m unittest discover -s tests -v
python3 scripts/check_repository.py
git diff --check
```

Review the staged files before committing. Game files, installers, saves,
generated runtimes and distribution archives must remain outside Git.

Shared documentation must work from a fresh checkout. Link to tracked files or
pinned public upstream sources. When documenting an ignored path, name the
tracked command that generates it or explain the private input the user must
supply. Local captures, review reports and one-off helpers belong in private
notes; shared findings must be understandable without opening those files.

## Releases

Create `release/<version>` from `develop` when a release is ready to stabilize.
Keep release fixes on that branch. After validation, merge it into `main`
through a pull request using a merge commit, and tag the resulting release
commit. Merge the release fixes back into `develop` through a pull request too.
Keep both permanent branches; remove the release branch only after both merges.

Binary releases must include the matching source archive, checksums and license
notices described in [BUILDING.md](BUILDING.md). Do not include commercial game
files or extracted artwork.

## Urgent release fixes

Create `hotfix/<version>` from `main`. Merge the fix into `main` through a pull
request using a merge commit, tag the corrected release, and merge the same fix
back into `develop` through a pull request. If a release branch is active,
bring the fix into that branch as well.

No direct commits or pushes to `main` are part of this workflow. Local branch
names do not prevent a local commit, but GitHub rejects direct updates to the
protected branch.
