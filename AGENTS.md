# Agent instructions

## Commits and versioning

Releases are automated with release-please (`.github/workflows/release-please.yml`). The version in `rag-service/pyproject.toml` is managed by it: never edit it by hand, and never bump it in a normal commit. On each push to `main` it reads the commit messages since the last release, opens or updates a "Release PR" with the bump and CHANGELOG, and merging that PR tags `vX.Y.Z`.

So every commit message must follow Conventional Commits (`type(optional-scope): summary`). Pick the type by what the change does for users of the app or API, not by the size of the diff:

| Type | Use for | Bump (while 0.x) |
|---|---|---|
| `feat:` | new user-visible capability, page, endpoint or option | minor (0.x.0) |
| `fix:` | bug fix, wrong behaviour corrected | patch (0.0.x) |
| `perf:` | faster, same behaviour | patch |
| `feat!:` / `fix!:` + `BREAKING CHANGE: ...` footer | removes or changes something callers rely on (API shape, route, env var, DB contract) | minor while 0.x, major after 1.0 |
| `refactor:` `docs:` `chore:` `ci:` `build:` `style:` `test:` | no change in behaviour | none (no release) |

- One logical change per commit; if a commit mixes a feat and a fix, use `feat:` (the bigger bump).
- Summary in the imperative, lowercase after the colon, no trailing period. Body explains why when it's not obvious.
- To jump to a specific version (e.g. 1.0.0), add a `Release-As: 1.0.0` footer.
- Do not commit with `[skip ci]`, and do not edit CHANGELOG.md or `.release-please-manifest.json` by hand.

Only commits that touch `rag-service/` count toward a release of the RAG service.
