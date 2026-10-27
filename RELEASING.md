# Releasing

Short reference for cutting a release. `PORTING.md` records *where the port
stands*; this file records *how to ship it*.

## The numbers, and where each one lives

There are three places a version can appear. They are not interchangeable.

| Where | Format | Example | Who reads it |
|---|---|---|---|
| Git tag | `v` + version | `v1.12.22` | Composer, GitHub releases, humans |
| `Zend_Version::VERSION` | bare version | `1.12.22` | code calling `compareVersion()` |
| `composer.json` `"version"` | — | *absent, by design* | nobody |

**The tag carries the `v`; the constant does not.** `Zend_Version::compareVersion()`
passes the constant straight to PHP's `version_compare()`, where a leading `v`
would change the comparison result. That is the entire reason for the split —
it is not a style choice.

**`composer.json` has no `"version"` key.** Composer derives the version from
the tag. A hardcoded copy drifts the moment someone forgets to bump it, and a
wrong `"version"` is worse than no key at all.

## What the number means

This port continues upstream's **1.12 line**. Upstream's last release was
`1.12.20`; the port's first was `1.12.21`. Every number after 1.12.20 is ours —
there is no corresponding Zend release, which is why the package is named
`maheshk-cyber/nbh-zf1` and not `zendframework/zendframework1`.

Patch-level bumps (`1.12.21` → `1.12.22`) are correct for this work: the public
`Zend_*` API is preserved, nothing is removed, and components that cannot run on
PHP 8 are documented-unavailable rather than deleted. That is a patch-level
contract under semver. A break in the ZF1 API would be a new major on a new
branch, not a continuation of `1.12.x`.

## Cut a release

Run from the repository root, on `1.12.x`.

**1. Bump the constant.** `library/Zend/Version.php`:

```php
const VERSION = '1.12.23';   // whatever the new number is
```

**2. Close out the CHANGELOG.** Move everything under `## [Unreleased]` down into
a new `## [1.12.23] - YYYY-MM-DD` heading, leaving `## [Unreleased]` empty above
it. The date is the release date, not the date work started.

**3. Refresh the measured block.** This rewrites the generated section of
`PORTING.md`:

```bash
tools/port-status.sh
```

**4. Run all three checks.** Do not tag on the strength of `port-status.sh`
alone — it reports, it does not gate.

```bash
find library -type f -name '*.php' -print0 | xargs -0 -n1 php -l
vendor/bin/phpcs library --standard=PHPCompatibility \
  --runtime-set testVersion 8.1-8.5 --report=summary
tools/port-status.sh --smoke
```

Expect **0 syntax failures**, and smoke counts **identical to the previous
release** unless a known-benign entry in `PORTING.md` says otherwise. A change
in the fatal count is a regression until proven not to be.

**5. Commit the release.** Message shape is established in `git log` — what
changed, why, what was verified. The maintainer is the sole author; no
`Co-Authored-By:` trailer.

**6. Tag, annotated, with a message.** Not a lightweight tag:

```bash
git tag -a v1.12.23 -m "1.12.23 — <one line on what this release contains>"
```

**7. Push the branch and the tag.** Both, or the tag exists only locally:

```bash
git push origin 1.12.x
git push origin v1.12.23
```

**8. Confirm they agree.** Cheap, and catches a tag made on the wrong commit:

```bash
git rev-list -n1 v1.12.23      # must equal:
git rev-parse origin/1.12.x
```

## Consuming the release

Consumers using a `type: package` repository name the tag in the dist URL:

```json
"repositories": [
    {
        "type": "package",
        "package": {
            "name": "maheshk-cyber/nbh-zf1",
            "version": "1.12.22",
            "dist": {
                "url": "https://api.github.com/repos/maheshk-cyber/nbh-zf1/zipball/v1.12.22",
                "type": "zip"
            },
            "autoload": { "psr-0": { "Zend_": "library/" } },
            "include-path": ["library/"],
            "require": { "php": ">=8.1", "ext-mbstring": "*", "ext-ctype": "*" }
        }
    }
]
```

Both `"version"` and the URL must name the same tag. `include-path` is not
optional — ZF1 looks classes up with bare `require_once 'Zend/Application.php'`,
and without it those lookups fail.

Because the constraint is `^1.12`, a patch release is picked up by
`composer update maheshk-cyber/nbh-zf1` with no change to the requiring app.

## Branch policy

`1.12.x` is the only active branch while the port is unstable — work is
committed and released there directly. `master` stays the untouched archived
upstream. Development branches come back once releases should stop moving under
existing consumers; see *Open decisions* in `PORTING.md`.
