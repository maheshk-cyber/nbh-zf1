# nbh-zf1 — porting ZF1 to modern PHP

This repo is a port of Zend Framework 1 to PHP 8.1+. **`PORTING.md` is the
source of truth for where the work stands**, and it is built to be resumed cold.

## If asked to "continue" / "resume from where we stopped" / "where are we"

Do this before touching anything:

1. Read `PORTING.md` — work queue, open decisions, known-benign smoke results.
2. `git status` and `git log --oneline -5` — the last batch may be uncommitted.
3. Run `tools/port-status.sh` to refresh the measured block.

Then take the first `TODO` item in the work queue. Do not re-derive the state
from scratch and do not re-do `DONE` items.

## Before claiming a change works

Three checks, all of them:

```bash
find library -type f -name '*.php' -print0 | xargs -0 -n1 php -l   # syntax
vendor/bin/phpcs library --standard=PHPCompatibility \
  --runtime-set testVersion 8.1-8.5 --report=summary                # compat
tools/port-status.sh --smoke                                        # class load
```

The upstream PHPUnit 3.x suite in `tests/` **cannot run on PHP 8**. Do not try
to resurrect it; `tools/smoke.php` is the regression check instead.

## When finishing a batch

1. `tools/port-status.sh` — refresh the numbers in `PORTING.md`.
2. Update the work queue and open decisions in `PORTING.md`.
3. Add an entry to `CHANGELOG.md` under `[Unreleased]`.
4. Commit. The commit message carries the same summary — see `git log` for the
   established shape (what changed, why, what was verified). The user is the
   sole author: **never add a `Co-Authored-By:` trailer.**

## Conventions

- Preserve the public `Zend_*` API. These fixes are compatibility shims, not
  redesigns.
- Prefer the smallest change that keeps observable behaviour identical. Where a
  rewrite is unavoidable, write it to be behaviour-identical and say so.
- Retired-extension components (mcrypt, sqlite2, wddx, oci8, `mysql_*`) are
  documented, not fixed — the extension is gone from PHP itself.
- Decisions that change the package contract go in *Open decisions* in
  `PORTING.md` rather than being made unilaterally.
