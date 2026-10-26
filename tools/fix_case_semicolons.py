#!/usr/bin/env python3
"""
Rewrite `case X;` / `default;` to `case X:` / `default:`.

PHP 8.5 deprecates a case statement terminated by a semicolon. The fix is a
single-character substitution on the line, and it is behaviour-identical:
the semicolon and the colon are alternative terminators for the same
statement.

Only a terminator is matched -- a `case` whose body begins on the same line
(`case 1: foo();`) is left alone, because there the semicolon belongs to the
body statement, not to the label.

Usage:
    tools/fix_case_semicolons.py library [--dry]
"""

import os
import re
import subprocess
import sys

# `case <expr>;` or `default;` where the semicolon is the LAST thing on the line.
# The expression may contain anything except a semicolon, so we anchor on the
# terminator being followed only by whitespace or a line comment.
CASE_SEMICOLON = re.compile(
    r'^(?P<indent>\s*)(?P<label>case\s+.+?|default)\s*;(?P<tail>\s*(?://.*|#.*)?)$'
)

# A colon outside quotes means the label already ended and this line has a body,
# so the trailing semicolon closes a statement rather than the label.
COLON_OUTSIDE_QUOTES = re.compile(r"""^[^'"]*(?:(?:'[^']*'|"[^"]*")[^'"]*)*:""")


def label_already_closed(label):
    """True if `label` contains a colon that ends the case label."""
    i = 0
    n = len(label)
    while i < n:
        c = label[i]
        if c in '"\'':
            quote = c
            i += 1
            while i < n:
                if label[i] == '\\':
                    i += 2
                    continue
                if label[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if c == ':':
            # `::` is part of a static reference, not a label terminator.
            if i + 1 < n and label[i + 1] == ':':
                i += 2
                continue
            if i > 0 and label[i - 1] == ':':
                i += 1
                continue
            return True
        i += 1
    return False


def fix_line(line):
    """Return (new_line, changed)."""
    stripped = line.rstrip('\n')
    m = CASE_SEMICOLON.match(stripped)
    if not m:
        return line, False
    label = m.group('label')
    # A body already on this line, or an expression that visibly continues.
    if label_already_closed(label):
        return line, False
    if label.rstrip().endswith(('?', ':', '.', ',', '|', '&', '(', '+', '-')):
        return line, False
    new = f"{m.group('indent')}{label}:{m.group('tail')}"
    return new + ('\n' if line.endswith('\n') else ''), True


def php_lint(path):
    proc = subprocess.run(['php', '-l', path], capture_output=True, text=True)
    return proc.returncode == 0 and 'Errors parsing' not in proc.stdout, proc.stdout + proc.stderr


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = sys.argv[1]
    dry = '--dry' in sys.argv

    files = 0
    sites = 0
    failures = []

    for dirpath, _, names in os.walk(root):
        for name in sorted(names):
            if not name.endswith('.php'):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding='utf-8', errors='surrogateescape') as fh:
                lines = fh.readlines()

            changed_here = 0
            for i, line in enumerate(lines):
                new, changed = fix_line(line)
                if changed:
                    lines[i] = new
                    changed_here += 1

            if not changed_here:
                continue

            files += 1
            sites += changed_here
            if dry:
                print(f'would fix {changed_here:3d} in {path}')
                continue

            with open(path, 'w', encoding='utf-8', errors='surrogateescape') as fh:
                fh.writelines(lines)

            ok, log = php_lint(path)
            if not ok:
                failures.append((path, log))
                print(f'LINT FAILED {path}\n{log}')
            else:
                print(f'fixed {changed_here:3d} in {path}')

    print(f'\n{files} files, {sites} case terminators{" (dry run)" if dry else ""}',
          file=sys.stderr)
    if failures:
        print(f'{len(failures)} lint failures', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
