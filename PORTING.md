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
| 19 | `Zend_Search_Lucene_MultiSearcher`: `$this` in `static` methods | 4 methods | DONE |
| 20 | **IObservable `func_get_args()` semantics (changed PHP 7)** | 42 sites | TODO |
| 21 | Optional-before-required params | 8 sites / 5 files | DONE |
| 22 | mcrypt users (`Crypt/Math`, `ReCaptcha/MailHide`, `Filter/Encrypt/Mcrypt`) | 3 files | DONE (documented-unavailable) |
| 23 | Retired extensions: `sqlite_*`, `oci_*`, `mysql_*`, `wddx` | ~10 files | WONTFIX |
| 24 | `Zend_Test_PHPUnit_*` targets PHPUnit 3.x | 26 classes | **DECIDE** |
| 25 | `Serializable` interface deprecated | 5 classes | DONE |
| 26 | `SplFixedArray`, `xml_set_object`, `imagedestroy`, `libxml_disable_entity_loader`, misc | 13 sites / 9 files | DONE |

Items 1–18 and 26 are in the working tree and are described in `CHANGELOG.md`.
Items 19–21 are mechanical or near-mechanical. Item 24 needs a product decision
— see *Open decisions*; item 22 has been decided (see below).
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

Item 19 could not be fixed by simply deleting `$this`. The four accessors are
declared `static` in `Zend_Search_Lucene_Interface`, and PHP refuses an
instance method in a position where a static one is required ("Cannot make
static method I::f() non static"), so they have to stay static — yet a
multisearcher has no instance to read `$_indices` from. On PHP 5/7 the `$this`
read was only a *notice* that evaluated to null, so `getDefaultSearchField()`
and `getResultSetLimit()` always threw "Indices list is empty" and the two
setters silently wrote to nothing. The fix records the index list in a static
mirror (`$_staticIndices`) whenever `__construct()` / `addIndex()` receives it,
giving the static accessors real state to read. This is the first deliberate
behaviour change in the port: those four methods go from "always broken" to
working. The instance-side state is untouched, and nothing in the tree calls
them, so the blast radius is limited to code that was already non-functional.

Item 25 keeps `implements Serializable` on all five classes and adds
`__serialize()` / `__unserialize()` **alongside** the legacy pair. Dropping the
interface — which is what the `RedundantSerializableImplementation` sniff
suggests once the magic methods exist — would make an object that no longer
serializes emit a *successful* empty `O:` payload instead of failing loudly,
and the interface is published API. The engine only suppresses the deprecation
when both are present, and once they are it stops routing new payloads through
`unserialize()`, which is the actual security win. Legacy `C:` payloads still
read correctly through the retained `unserialize()`; that path is exercised by
probe for `Zend_Http_UserAgent`, `Zend_Stdlib_PriorityQueue` and
`Zend_Stdlib_SplPriorityQueue`. `Zend_Stdlib_SplPriorityQueue::serialize()`
was additionally refactored so it and `__serialize()` share one drain-and-
reinsert helper rather than duplicating the destructive-loop idiom twice.

`phpcs.xml.dist` was added so the ledger number can be reproduced and so the
two Serializable sniffs can be configured rather than hand-waved:
`Zend_Http_UserAgent_Device` is registered as a serializable interface (the
sniff cannot otherwise know that its 14 implementors inherit the deprecation),
and `RedundantSerializableImplementation` is disabled with the reasoning above
recorded in the file. `tools/port-status.sh` still passes
`--standard=PHPCompatibility` explicitly, so the ledger stays comparable across
batches; pass `--standard=phpcs.xml.dist` to see the configured number.

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

1. **mcrypt components — RESOLVED (option b, with hardening).**
   `Zend_Crypt_Math`, `Zend_Service_ReCaptcha_MailHide` and
   `Zend_Filter_Encrypt_Mcrypt` depend on `ext-mcrypt`, removed from PHP in
   7.2. Porting to openssl (option a) is real crypto work that would change
   ciphertext and needs review, so the documented-unavailable stance stands —
   with three corrections that make the failure a clean one:
   - `Zend_Crypt_Math::randBytes()`'s `mcrypt_create_iv()` fallback was
     unreachable (it sat behind `function_exists('random_bytes')`, which PHP 7+
     always satisfies) and is deleted.
   - `Zend_Service_ReCaptcha_MailHide`'s `ENCRYPTION_MODE`/`ENCRYPTION_CIPHER`
     constants were `MCRYPT_MODE_CBC`/`MCRYPT_RIJNDAEL_128` — reading either on
     a build without mcrypt throws `Undefined constant`, so the class could not
     even be instantiated to reach its own `_requireMcrypt()` guard. They are
     now the literals `'cbc'` and `'rijndael-128'`, which are the values mcrypt
     used for them.
   - `Zend_Filter_Encrypt_Mcrypt` guards its constructor but not its public
     `setEncryption()`; both now raise the same explicit
     `Zend_Filter_Exception` naming `Zend_Filter_Encrypt_Openssl` as the
     alternative.

   The remaining phpcs hits in these files are the deliberate, documented
   absence of the extension — not something to chase.
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
_Refreshed 2026-10-26 18:20 UTC_

| | |
|---|---|
| Branch | `star-php85` @ `8f73ad87` — Unbreak MultiSearcher static accessors; add __serialize to Serializable classes |
| Uncommitted files | 3 |
| Library files | 2264 |
| Syntax failures | 0 |
| PHPCompatibility (8.1-8.5) | **197 errors, 76 warnings** (273 total) |

**Class-load smoke**: not run in this refresh — run `tools/port-status.sh --smoke` to include it.


### Remaining violations by sniff

| Count | Type | Sniff |
|---|---|---|
| 42 | error | `FunctionUse.ArgumentFunctionsReportCurrentValue.Changed` |
| 17 | error | `Extensions.RemovedExtensions.sqliteRemoved` |
| 16 | error | `FunctionUse.RemovedFunctions.oci_errorRemoved` |
| 14 | error | `Extensions.RemovedExtensions.mcryptDeprecatedRemoved` |
| 7 | warning | `and possibly changed (by reference)` |
| 7 | warning | `IniDirectives.RemovedIniDirectives.mbstring_func_overloadDeprecatedRemoved` |
| 6 | warning | `FunctionDeclarations.RemovedImplicitlyNullableParam.Deprecated` |
| 5 | error | `FunctionUse.RemovedFunctions.sqlite_fetch_singleRemoved` |
| 5 | error | `Constants.RemovedConstants.sqlite_assocRemoved` |
| 5 | warning | `FunctionUse.RemovedFunctions.xml_parser_freeDeprecated` |
| 4 | error | `Extensions.RemovedExtensions.mysql_DeprecatedRemoved` |
| 4 | error | `FunctionUse.RemovedFunctions.sqlite_fetch_arrayRemoved` |

<!-- STATUS:END -->
