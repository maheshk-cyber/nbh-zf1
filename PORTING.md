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
| 13 | Semicolon-terminated `case` statements | 138 sites, 38 files | TODO |
| 14 | Non-canonical casts `(integer)` / `(boolean)` / `(double)` | 84 sites | TODO |
| 15 | `${var}` string interpolation | 8 sites, 5 files | TODO |
| 16 | `$php_errormsg` + `track_errors` (removed PHP 8) | 7 files | TODO |
| 17 | `utf8_encode()` / `utf8_decode()` deprecated 8.2 | 11 sites | TODO |
| 18 | `iconv_set_encoding()` with removed encodings | 11 sites | TODO |
| 19 | `Zend_Search_Lucene_MultiSearcher`: `$this` in `static` methods | 4 methods | TODO |
| 20 | **IObservable `func_get_args()` semantics (changed PHP 7)** | 42 sites | TODO |
| 21 | Optional-before-required params | 8 sites | TODO |
| 22 | mcrypt users (`Crypt/Math`, `ReCaptcha/MailHide`) | 2 files | **DECIDE** |
| 23 | Retired extensions: `sqlite_*`, `oci_*`, `mysql_*`, `wddx` | ~10 files | WONTFIX |
| 24 | `Zend_Test_PHPUnit_*` targets PHPUnit 3.x | 26 classes | **DECIDE** |
| 25 | `Serializable` interface deprecated | 4 sites | TODO |
| 26 | `SplFixedArray`, `xml_set_object`, `imagedestroy`, misc | scattered | TODO |

Items 1–12 are in the working tree and are described in `CHANGELOG.md`.
Items 13–21 are mechanical or near-mechanical. Items 22 and 24 need a product
decision — see *Open decisions*.

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
   `Zend_Serializer_Adapter_Wddx`, the `oci8`/`mysql_*` helpers, and
   `Zend_Pdf`'s `track_errors` paths cannot work regardless of syntax. Current
   stance: leave in tree, document, do not chase phpcs errors in them.

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
_Refreshed 2026-10-26 11:57 UTC_

| | |
|---|---|
| Branch | `star-php85` @ `dea63a30` — Package as maheshk-cyber/nbh-zf1 for PHP 8.1+ |
| Uncommitted files | 179 |
| Library files | 2264 |
| Syntax failures | 0 |
| PHPCompatibility (8.1-8.5) | **249 errors, 354 warnings** (603 total) |

**Class-load smoke** (`tools/smoke.php`): 2217 load clean, 37 fatal, 4 missing.
See the *Known-benign smoke results* section before treating a fatal as a regression.


### Remaining violations by sniff

| Count | Type | Sniff |
|---|---|---|
| 138 | warning | `ControlStructures.RemovedTerminatingCaseWithSemicolon.Deprecated` |
| 45 | warning | `TypeCasts.RemovedTypeCasts.integerDeprecated` |
| 42 | error | `FunctionUse.ArgumentFunctionsReportCurrentValue.Changed` |
| 37 | warning | `TypeCasts.RemovedTypeCasts.booleanDeprecated` |
| 31 | error | `IniDirectives.RemovedIniDirectives.track_errorsDeprecatedRemoved` |
| 17 | error | `Extensions.RemovedExtensions.sqliteRemoved` |
| 16 | error | `FunctionUse.RemovedFunctions.oci_errorRemoved` |
| 15 | error | `Extensions.RemovedExtensions.mcryptDeprecatedRemoved` |
| 13 | error | `Variables.RemovedPredefinedGlobalVariables.php_errormsgDeprecatedRemoved` |
| 11 | warning | `ParameterValues.RemovedIconvEncoding.DeprecatedValueFound` |
| 8 | warning | `FunctionDeclarations.RemovedOptionalBeforeRequiredParam.Deprecated80` |
| 8 | warning | `TextStrings.RemovedDollarBraceStringEmbeds.DeprecatedVariableSyntax` |

<!-- STATUS:END -->
