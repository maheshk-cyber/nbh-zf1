#!/usr/bin/env python3
"""Rewrite the `@ini_set('track_errors', ...)` / `@ini_restore(...)` brackets in
Zend_Feed and Zend_Gdata_App to use error_get_last().

The pattern these files share is:

    @ini_set('track_errors', 1);
    <one statement, suppressed with @>
    @ini_restore('track_errors');
    if (<sentinel test>) {
        ... 'some text: ' . "$php_errormsg" ...
    }

track_errors was removed in PHP 8.0, so the two ini calls are inert; the
message has to come from error_get_last(). error_clear_last() goes first so a
stale error from an earlier call is not mistaken for this one's.

Idempotent: files already rewritten contain no track_errors bracket to match.
"""

import re
import sys

BRACKET = re.compile(
    r'@ini_set\(\s*[\'"]track_errors[\'"]\s*,\s*1\s*\);\n'
    r'(?P<body>(?:.*?\n)*?)'
    r'(?P<indent>[ \t]*)@ini_restore\(\s*[\'"]track_errors[\'"]\s*\);\n'
)

PHPERRORMSG = re.compile(r'\$php_errormsg')


def rewrite(path, dry_run=False):
    with open(path) as fh:
        src = fh.read()

    original = src
    changed = 0

    def repl(m):
        nonlocal changed
        body = m.group('body')
        changed += 1
        # No indent prefix here: the whitespace that preceded @ini_set sits
        # outside the match and is preserved, so adding it again would double up.
        return 'error_clear_last();\n%s' % body

    src = BRACKET.sub(repl, src)

    if changed and PHPERRORMSG.search(src):
        # Replace the remaining $php_errormsg reads. Each sits inside a branch
        # guarded by the sentinel test, so two lines hoist the message.
        src = re.sub(
            r'\$php_errormsg',
            "$errorMessage",
            src,
        )
        # Insert the two hoisting lines immediately before each throw that now
        # references $errorMessage -- only where not already hoisted.
        src = re.sub(
            r'(?P<indent>[ \t]*)(?P<throw>throw new \w+\(\s*\n?\s*"[^"]*\$errorMessage)',
            lambda m: (
                '%s$error = error_get_last();\n'
                '%s$errorMessage = $error === null ? \'(error message not available)\' : $error[\'message\'];\n'
                '%s%s' % (m.group('indent'), m.group('indent'), m.group('indent'), m.group('throw'))
            ),
            src,
        )

    if src == original:
        print('  unchanged  %s' % path)
        return False

    if not dry_run:
        with open(path, 'w') as fh:
            fh.write(src)
    print('  %s  %s (%d bracket%s)' % ('would fix' if dry_run else 'fixed    ', path, changed, '' if changed == 1 else 's'))
    return True


def main(argv):
    dry_run = '--dry-run' in argv
    paths = [a for a in argv if not a.startswith('--')]
    if not paths:
        print(__doc__)
        return 2
    any_changed = False
    for path in paths:
        any_changed |= rewrite(path, dry_run)
    return 1 if any_changed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
