# ADR-0005: Auto-discover `config.yaml` when `-c` is omitted
Status: Accepted
Date: 2026-06-02

## Context
Previously `load_config(None)` returned a default `AppConfig` whose FMC host
was the placeholder `fmc.example.local`. Forgetting `-c config.yaml` on the
CLI silently produced DNS lookup failures (`NameResolutionError`) and the
web UI booted with a non-working FMC config until the user manually saved
one. This was an easy mistake that gave a confusing error.

A passing `-c <path>` with a non-existent file was *also* silently ignored
— same problem, different user mistake.

## Decision
- When `path is None`, search in order and use the first existing file:
  1. `$NGFW_APPDETECTOR_CONFIG` (explicit env override)
  2. `./config.yaml`
  3. `./config.yml`
  4. `~/.config/ngfw-appdetector/config.yaml`
  If nothing is found, fall back to defaults (existing behavior, but now
  rare in practice).
- When `path is not None` and the file doesn't exist, raise `FileNotFoundError`.
  Don't silently fall through to defaults.

Implementation: `_discover_config()` + revised `load_config()` in
`src/ngfw_appdetector/config.py`.

## Consequences
+ `ngfw-appdetector serve` (without `-c`) "just works" when run from the
  project root or after dropping a config in `~/.config/ngfw-appdetector/`.
+ Typos in `-c` paths fail loudly instead of silently using placeholder
  defaults.
+ Env-based deployments can point at any config via
  `NGFW_APPDETECTOR_CONFIG=/etc/ngfw/config.yaml`.
- Behavior depends on `cwd`. Documented in [AGENTS.md](../../AGENTS.md) and
  [README.md](../../README.md). Acceptable trade-off for a dev/lab tool.

## Alternatives considered
- **Require `-c` always**: explicit but annoying for the common case.
- **Search XDG paths first**: would surprise users who keep a `config.yaml`
  next to the repo; reversed the order so cwd wins.
- **Generate a default `config.yaml` on first run**: lifecycle headache
  (where? overwrite? prompt?) for very little gain — `config.example.yaml`
  is already shipped.
