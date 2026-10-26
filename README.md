# nbh-zf1 — Zend Framework 1 for modern PHP

A maintained port of Zend Framework 1, packaged for Composer and updated to run
on current PHP versions while preserving the original `Zend_*` class names and
public API.

- **Package:** `maheshk-cyber/nbh-zf1`
- **Supported PHP:** 8.1 – 8.5
- **Autoloading:** PSR-0 for the `Zend_` prefix, plus Composer `include-path`
- **License:** BSD-3-Clause (unchanged from upstream ZF1)

## Why this package exists

Upstream Zend Framework 1 reached end of life in September 2016 and was archived
at version 1.12.20. It does not run on PHP 8. This package keeps the framework
usable as a dependency for applications that have not yet migrated away from ZF1.

## Requirements

| Requirement | Version |
|---|---|
| PHP | 8.1 or later (tested through 8.5) |
| `ext-mbstring` | required |
| `ext-ctype` | required |

Optional components require their own extensions — for example `pdo_mysql` for
`Zend_Db_Adapter_Pdo_Mysql`, `openssl` for the crypt filters, and `dom`/`simplexml`
for the feed and XML components.

## Installation

```bash
composer require maheshk-cyber/nbh-zf1
```

Then load Composer's autoloader as usual:

```php
require __DIR__ . '/vendor/autoload.php';

$acl = new Zend_Acl();
```

ZF1 resolves many dependencies through `require_once 'Zend/....php'` relative to
`include_path`. This package declares `include-path` in its `composer.json`, so
Composer adds the library directory to `include_path` automatically — no manual
`set_include_path()` call is needed. This behaviour is verified by installing the
package into a clean project and autoloading without any additional bootstrap.

If you vendor this package into a non-Composer context, you must set the include
path yourself:

```php
set_include_path('/path/to/nbh-zf1/library' . PATH_SEPARATOR . get_include_path());
```

## Compatibility status

| PHP version | Status |
|---|---|
| 8.1 | target floor |
| 8.2 | supported |
| 8.3 | supported |
| 8.4 | supported — emits deprecation notices, see below |
| 8.5 | **primary target**, fully syntax-clean |

All 2,264 library files parse cleanly under PHP 8.5.

### Known limitations

- **Deprecation notices on PHP 8.4+.** Some methods do not declare return types
  compatible with their SPL parents (e.g. `Zend_Registry::offsetExists()` against
  `ArrayObject`), and some legacy casts such as `(integer)` and `(boolean)` are
  deprecated. These are notices, not errors, and are being addressed.
- **Removed extensions.** Components built on `mcrypt`, `wddx`, SQLite 2, the
  original `mysql_*` API, and `track_errors` cannot work on PHP 8, as those
  extensions were removed from PHP itself. Affected classes remain in the tree
  but should be considered unavailable:
  - `Zend_Filter_Encrypt_Mcrypt`
  - `Zend_Serializer_Adapter_Wddx`
  - `Zend_Cache_Backend_Sqlite`
  - `Zend_Db_Adapter_Mysqli`'s legacy `mysql_*` helpers
- **`func_get_args()` semantics.** Since PHP 7, functions that inspect their
  arguments observe the current value rather than the value as passed. A number of
  legacy validators rely on the old behaviour and may misreport argument details.
- **No automated test suite yet.** The upstream PHPUnit 3.x tests are still in
  `tests/` for reference but do not run on PHP 8.1+. Characterization tests for
  the components in active use are in progress.

## Development

```bash
composer install

# Syntax check all files
find library -type f -name '*.php' -print0 | xargs -0 -n1 php -l

# Compatibility scan (adjust the range as needed)
vendor/bin/phpcs library \
  --standard=PHPCompatibility \
  --runtime-set testVersion 8.1-8.5 \
  --report=summary
```

PHP versions 8.1 through 8.5 are exercised in CI.

## Reporting issues

Please include the PHP version, the component involved, and a minimal reproduction.

## Credits

Zend Framework 1 was created by Zend Technologies and contributed to by many
people. This port builds directly on that work. See `LICENSE.txt` for the original
license.
