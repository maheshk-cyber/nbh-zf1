# Porting ledger — ZF1 on PHP 8.1+

This file is the **single source of truth for where the port stands**. It is
written so that any agent or developer can resume cold, without conversation
history. If you are asked to "resume from where we stopped", read this file
first, then run the verification commands below.

The measured block near the bottom is generated — never hand-edit it.

---

## How to resume

```bash
cd ~/www/nbh-zf1
git status                 # uncommitted work from the last batch, if any
git log --oneline -5       # last committed batch
tools/port-status.sh       # refresh the measured block in this file (fast)
```

Then pick the first **not-started** item from *Work queue* below and go.
When a batch is finished: run `tools/port-status.sh`, update *Work queue* and
*Decision log*, and commit — the commit message carries the same summary.

---

## Verification

The upstream PHPUnit 3.x suite in `tests/` **cannot run on PHP 8** — do not try
to resurrect it. Verification is these three commands:

| Purpose | Command | Cost |
|---|---|---|
| Syntax | `find library -type f -name '*.php' -print0 \| xargs -0 -n1 php -l` | ~1 min |
| Compatibility | `vendor/bin/phpcs library --standard=PHPCompatibility --runtime-set testVersion 8.1-8.5 --report=summary` | ~25 s |
| Class load | `tools/smoke.php --chunk=300 --offset=N` for N in 0,300,…,2100 | ~7 min |

`tools/smoke.php` autoloads every class in a forked subprocess and reports
`OK` / `MISSING` / `FATAL` / `DEPRECATION`. A `FATAL` there is a class that
cannot even be declared — the highest-severity signal the port has.

**A fix is not done until syntax + phpcs + smoke have all been re-run.**

---

## Work queue

Status: `TODO` / `WIP` / `DONE` / `WONTFIX`.

| # | Item | Where | Status |
|---|---|---|---|
| 1 | Curly-brace string offsets (`$s{0}` → `$s[0]`) | 18 files | DONE |
| 2 | `unset($this)`, nested unparenthesised ternaries | 2 files | DONE |
| 3 | PHP 8 fatal: `Zend_Rest_Route::assemble()` LSP violation | `Rest/Route.php` | DONE |
| 4 | PHP 8 fatal: `Zend_Soap_Client_Common::__doRequest()` vs SPL | `Soap/Client/Common.php` | DONE |
| 5 | PHP 8 fatal: WindowsAzure log writer referenced 3 non-existent classes | `Service/WindowsAzure/Log/Writer/` | DONE |
| 6 | `each()` removed in PHP 8 | 4 files | DONE |
| 7 | `create_function()` removed in PHP 8 | `Feed/Element.php` | DONE |
| 8 | `get_magic_quotes_gpc()` removed in PHP 5.4 | `Tool/Project/Provider/DbAdapter.php` | DONE |
| 9 | `continue` targeting `switch` (→ `continue 2`) | 10 sites, 6 files | DONE |
| 10 | Bug: `count()` on a string | `Config/Yaml.php` | DONE |
| 11 | Bug: infinite recursion on empty XML-RPC `<value/>` | `XmlRpc/Value.php` | DONE |
| 12 | Implicitly-nullable params (`Foo $x = null` → `?Foo $x = null`) | 147 files, 272 params | DONE |
| 13 | Semicolon-terminated `case` statements | 138 sites, 38 files | DONE |
| 14 | Non-canonical casts `(integer)` / `(boolean)` / `(double)` | 122 sites, 53 files | DONE |
| 15 | `${var}` string interpolation | 8 sites, 5 files | DONE |
| 16 | `$php_errormsg` + `track_errors` (removed PHP 8) | 31 sites / 11 files | DONE |
| 17 | `utf8_encode()` / `utf8_decode()` deprecated 8.2 | 11 sites / 7 files | DONE |
| 18 | `iconv_set_encoding()` with removed encodings | 11 sites / 5 files | DONE |
| 19 | `Zend_Search_Lucene_MultiSearcher`: `$this` in `static` methods | 4 methods | TODO |
| 20 | **IObservable `func_get_args()` semantics (changed PHP 7)** | 42 sites | TODO |
| 21 | Optional-before-required params | 8 sites / 5 files | DONE |
| 22 | mcrypt users (`Crypt/Math`, `ReCaptcha/MailHide`) | 2 files | **DECIDE** |
| 23 | Retired extensions: `sqlite_*`, `oci_*`, `mysql_*`, `wddx` | ~10 files | WONTFIX |
| 24 | `Zend_Test_PHPUnit_*` targets PHPUnit 3.x | 26 classes | **DECIDE** |
| 25 | `Serializable` interface deprecated | 4 sites | TODO |
| 26 | `SplFixedArray`, `xml_set_object`, `imagedestroy`, `libxml_disable_entity_loader`, misc | 13 sites / 9 files | DONE |

Items 1–18 and 26 are in the working tree and are described in `CHANGELOG.md`.
Items 19–21 are mechanical or near-mechanical. Items 22 and 24 need a product
decision — see *Open decisions*.

Item 18 turned out to be dead-code removal rather than a port. Every one of the
11 `iconv_set_encoding()` sites was already inside a `PHP_VERSION_ID < 50600`
branch with the `ini_set('default_charset', ...)` alternative in the `else`, so
on PHP 8 none of them had executed for years. The conditional and the iconv
branch are deleted, leaving the `ini_set` path that was already running. No
behaviour changes; this is why the snapshot at time of writing showed only a
deprecation warning per site and no risk.

Item 17 has one deliberate asymmetry worth knowing before touching it again.
`utf8_encode()` and `mb_convert_encoding($s, 'UTF-8', 'ISO-8859-1')` are exactly
equivalent — 0 differences across 3,262 fuzzed samples including every single
byte 0x00–0xFF. `utf8_decode()` is **not** equivalent to
`mb_convert_encoding($s, 'ISO-8859-1', 'UTF-8')` on malformed input: they insert
a different number of substitute characters (192 differences in the same corpus).
The two agree on every well-formed UTF-8 string (0 differences across 20,000
generated valid samples), and the five `utf8_decode()` sites read an Azure
service-configuration XML file that declares `encoding="utf-8"`, so well-formed
input is the only input that path is meant to receive. If such a file is ever
malformed, the exception text may differ by a character or two — nothing else.

Item 26 is done and worth reading before touching XML error reporting again.
Removing `libxml_disable_entity_loader()` had a side effect on the item-16
rewrites: the call used to emit a deprecation *after* the caller's
`error_clear_last()`, so `error_get_last()` reported the deprecation text as the
parse failure's "cause". Removing it left the message empty, because `scan()`
parses with libxml's internal error buffer and that error never reaches PHP's
last-error slot. `scan()` now reads `libxml_get_last_error()` and re-raises it
with `@trigger_error(E_USER_WARNING)`, which populates the slot without printing
— so every caller of item-16's pattern gets the real parse error, and none of
the callers that do not print warnings start printing them. That `@` is load
bearing; removing it makes `Zend_Feed::importString()` leak a warning to stdout
on every malformed feed.

The XXE question was settled by measurement, not by assumption: on PHP 8 external
entities are not resolved by default (`&xxe;` yields an empty text node where a
PHP 5/7 build would have inlined `/etc/passwd`), and `scan()` independently
rejects any DOCTYPE that declares an entity. Both were re-tested after the
change.

Item 21 was **not** solved by one uniform edit, because the textbook fix
(delete the `= null` and make the parameter genuinely required) turns a clean
catchable exception into a fatal `ArgumentCountError` on exactly the error path
the optional parameter existed to report. Two shapes were used instead:

- Where the method already validates the argument and throws, the default was
  simply removed — the validation runs first, so behaviour on bad input is
  unchanged. `Pdf/Element/Reference::__construct()`,
  `Storage/Queue::deleteMessage()`, and
  `Diagnostics/Manager::setConfigurationForRoleInstance()` are these.
- Where the signature is bound by `Zend_Service_Console_Command`'s reflection
  model (`@command-parameter-for` annotations, positional binding), the
  optional parameters were **reordered to the end** rather than made required.
  Reordering is safe there precisely because the console binds by position and
  documents by annotation: the three `CommandLine/*` methods keep every
  parameter optional and keep their CLI flags working.

Verifying item 21 turned up an unrelated PHP 8 fatal that the class-load smoke
cannot see: `Zend_Service_Console_Command` assembled its parameter list with a
**named** key (`$parameterValues['argv'] = ...`), and PHP 8 rejects unknown
named arguments outright — `Error: Unknown named parameter $argv` — because no
handler method declares an `$argv` parameter. It is now appended positionally,
which keeps it reachable by catch-all handlers and leaves every other method's
binding untouched. The `Deployment` and `Certificate` help screens were rendered
end to end afterwards to confirm the reflection model still builds and orders
every parameter correctly.

---

## Open decisions

These change the package's contract or scope, so they are not fixed unilaterally.

1. **mcrypt components.** `Zend_Crypt_Math` and
   `Zend_Service_ReCaptcha_MailHide` require `ext-mcrypt`, removed from PHP in
   7.2. Options: (a) port to openssl — real crypto work, needs review;
   (b) leave in tree, document as unavailable. Currently (b) is the README
   stance.
2. **`Zend_Test_PHPUnit_*`.** 26 classes target PHPUnit 3.x APIs
   (`PHPUnit_Framework_TestCase`). Options: (a) port to PHPUnit 10;
   (b) mark the package as PHPUnit-3-only / drop; (c) leave broken and
   documented. Unrelated to the "runs on PHP 8" goal.
3. **Retired-extension components.** `Zend_Cache_Backend_Sqlite`,
   `Zend_Serializer_Adapter_Wddx`, the `oci8`/`mysql_*` helpers cannot work
   regardless of syntax. Current stance: leave in tree, document, do not chase
   phpcs errors in them.

---

## Known-benign smoke results

Do not treat these as regressions; they are pre-existing and expected.

- The **26 `Zend_Test_PHPUnit_*` fatals** — PHPUnit 3.x is not installed.
- **~11 filename/class mismatches** shipped by upstream, where the file name
  does not match the declared class so PSR-0 autoloading cannot find it.
  Examples: `Gdata/Analytics/Extension/Goal.php` declares
  `Zend_Gdata_Analytics_Goal`; `Gdata/App/FeedSourceParent.php` declares
  `Zend_Gdata_App_FeedSourceParent`.
- **4 `Zend_Validate_Hostname_*` "missing"** — `Biz.php`, `Cn.php`, `Com.php`,
  `Jp.php` are data fragments included by the parent class, not classes.
- **~10 000 deprecation notices** — every remaining deprecation shows up once
  per class that *loads* the offending file, so the smoke count overstates the
  true number of sites. Use phpcs for the real count.

---

<!-- STATUS:BEGIN (generated by tools/port-status.sh — do not hand-edit) -->
_Refreshed 2026-10-26 17:50 UTC_

| | |
|---|---|
| Branch | `star-php85` @ `25857e16` — Refresh porting ledger to post-commit state |
| Uncommitted files | 6 |
| Library files | 2264 |
| Syntax failures | 0 |
| PHPCompatibility (8.1-8.5) | **210 errors, 76 warnings** (286 total) |

**Class-load smoke**: not run in this refresh — run `tools/port-status.sh --smoke` to include it.


### Remaining violations by sniff

| Count | Type | Sniff |
|---|---|---|
| 42 | error | `FunctionUse.ArgumentFunctionsReportCurrentValue.Changed` |
| 17 | error | `Extensions.RemovedExtensions.sqliteRemoved` |
| 16 | error | `FunctionUse.RemovedFunctions.oci_errorRemoved` |
| 15 | error | `Extensions.RemovedExtensions.mcryptDeprecatedRemoved` |
| 8 | error | `Variables.ForbiddenThisUseContexts.OutsideObjectContext` |
| 7 | warning | `and possibly changed (by reference)` |
| 7 | warning | `IniDirectives.RemovedIniDirectives.mbstring_func_overloadDeprecatedRemoved` |
| 6 | warning | `FunctionDeclarations.RemovedImplicitlyNullableParam.Deprecated` |
| 5 | error | `FunctionUse.RemovedFunctions.sqlite_fetch_singleRemoved` |
| 5 | error | `Constants.RemovedConstants.sqlite_assocRemoved` |
| 5 | warning | `FunctionUse.RemovedFunctions.xml_parser_freeDeprecated` |
| 4 | error | `Extensions.RemovedExtensions.mysql_DeprecatedRemoved` |

<!-- STATUS:END -->
