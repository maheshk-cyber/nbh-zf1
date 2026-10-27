#!/usr/bin/env python3
"""
Add explicit nullable types to typed parameters whose default is null.

PHP 8.4 deprecates `function f(Foo $x = null)`; the explicit form is
`function f(?Foo $x = null)`. Only parameters that already carry a type are
touched -- untyped `$x = null` is unaffected and unflagged.

Usage:
    tools/fix_nullable_params.py library        # rewrite in place
    tools/fix_nullable_params.py library --dry  # report only
"""

import re
import sys
import os
import subprocess

# A typed parameter ending in a null default. Captures the leading type and the
# optional by-reference marker, keeping whitespace so the rewrite is minimal.
PARAM = re.compile(
    r'(?P<type>[A-Za-z_\\][A-Za-z0-9_\\|]*)\s+(?P<ref>&\s*)?(?P<var>\$\w+)\s*=\s*null\s*$'
)

# Detects a parameter that already carries a leading nullable marker.
ALREADY_NULLABLE = re.compile(r'(?<![A-Za-z0-9_\\])?\s*[A-Za-z_\\]')


def find_function_params(src):
    """Yield (start, end) offsets of each parameter list in the source."""
    for m in re.finditer(r'\bfunction\b', src):
        i = m.end()
        n = len(src)
        # Skip a by-reference marker before the function name.
        while i < n and src[i] in ' \t\n&':
            i += 1
        # Skip the function name.
        while i < n and (src[i].isalnum() or src[i] == '_'):
            i += 1
        while i < n and src[i] in ' \t\n':
            i += 1
        if i >= n or src[i] != '(':
            continue
        # Match the balanced parameter list.
        depth = 0
        start = i + 1
        j = i
        while j < n:
            c = src[j]
            if c in '"\'':
                quote = c
                j += 1
                while j < n:
                    if src[j] == '\\':
                        j += 2
                        continue
                    if src[j] == quote:
                        break
                    j += 1
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    yield start, j
                    break
            j += 1


def split_top_level(text):
    """Split a parameter list on commas that are not nested."""
    parts = []
    depth = 0
    current = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in '"\'':
            quote = c
            current.append(c)
            i += 1
            while i < n:
                current.append(text[i])
                if text[i] == '\\' and i + 1 < n:
                    current.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        if c == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
            i += 1
            continue
        current.append(c)
        i += 1
    parts.append(''.join(current))
    return parts


def fix_text(src):
    out = src
    offset = 0
    for start, end in find_function_params(src):
        params = src[start:end]
        if '= null' not in params and '=null' not in params:
            continue
        pieces = split_top_level(params)
        changed = False
        for idx, piece in enumerate(pieces):
            m = PARAM.search(piece)
            if not m:
                continue
            type_text = m.group('type')
            pos = piece.find(type_text)
            # Look at the text just before the type for an existing marker.
            before = piece[:pos].rstrip()
            if before.endswith('?') or '?' in before:
                continue
            if type_text.lower() == 'mixed':
                continue
            if '|' in type_text:  # already a union including null
                continue
            pieces[idx] = piece[:pos] + '?' + piece[pos:]
            changed = True
        if changed:
            new_params = ','.join(pieces)
            abs_start = start + offset
            abs_end = end + offset
            out = out[:abs_start] + new_params + out[abs_end:]
            offset += len(new_params) - (end - start)
    return out


def php_lint(path):
    proc = subprocess.run(
        ['php', '-l', path], capture_output=True, text=True
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = sys.argv[1]
    dry = '--dry' in sys.argv

    changed_files = 0
    changed_params = 0
    failures = []

    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith('.php'):
                continue
            path = os.path.join(dirpath, name)
            src = open(path, encoding='utf-8', errors='surrogateescape').read()
            new = fix_text(src)
            if new == src:
                continue
            delta = new.count('= null') + new.count('=null') - src.count('= null') - src.count('=null')
            changed_files += 1
            changed_params += len(re.findall(r'\?\s*[A-Za-z_\\][A-Za-z0-9_\\]*\s+(?:&\s*)?\$\w+\s*=\s*null', new)) \
                - len(re.findall(r'\?\s*[A-Za-z_\\][A-Za-z0-9_\\]*\s+(?:&\s*)?\$\w+\s*=\s*null', src))
            if dry:
                print(f'would change {path}')
                continue
            open(path, 'w', encoding='utf-8', errors='surrogateescape').write(new)
            ok, log = php_lint(path)
            if not ok:
                failures.append((path, log))
                print(f'LINT FAILED {path}\n{log}')
            else:
                print(f'changed {path}')

    print(f'\n{changed_files} files, {changed_params} parameters'
          f'{" (dry run)" if dry else ""}', file=sys.stderr)
    if failures:
        print(f'{len(failures)} lint failures', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
