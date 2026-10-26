#!/usr/bin/env php
<?php
/**
 * Class-load smoke test for the ZF1 port.
 *
 * The upstream PHPUnit 3.x suite cannot run on modern PHP, so this harness
 * checks the one thing that must hold for every file in library/: the class
 * must declare and autoload without raising a fatal Error or a deprecation.
 *
 * Usage:
 *   php tools/smoke.php [--chunk=N] [--offset=N] [--list]
 *
 * Each class is loaded in a forked subprocess so that an uncatchable fatal
 * (e.g. an incompatible method signature) does not abort the whole run.
 */

$root = dirname(__DIR__);
require $root . '/vendor/autoload.php';

$opts = getopt('', ['chunk::', 'offset::', 'list', 'filter::']);
$chunk  = isset($opts['chunk']) ? (int) $opts['chunk'] : 50;
$offset = isset($opts['offset']) ? (int) $opts['offset'] : 0;
$filter = $opts['filter'] ?? null;

$classes = [];
$it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root . '/library'));
foreach ($it as $file) {
    if ($file->getExtension() !== 'php') {
        continue;
    }
    $rel = substr($file->getPathname(), strlen($root . '/library/'), -4);
    if ($filter !== null && stripos($rel, $filter) === false) {
        continue;
    }
    $classes[] = str_replace('/', '_', $rel);
}
sort($classes);

if (isset($opts['list'])) {
    echo implode("\n", $classes), "\n";
    exit(0);
}

$slice = array_slice($classes, $offset, $chunk);

// Child process: load one class and report.
$childScript = <<<'PHP'
<?php
require $argv[1] . '/vendor/autoload.php';
$errors = [];
set_error_handler(function ($no, $str) use (&$errors) {
    $errors[] = $str;
    return true;
});
$class = $argv[2];
register_shutdown_function(function () use ($class) {
    $e = error_get_last();
    if ($e && in_array($e['type'], [E_ERROR, E_COMPILE_ERROR, E_PARSE], true)) {
        fwrite(STDOUT, "FATAL\t" . $class . "\t" . str_replace("\n", ' ', $e['message']) . "\n");
    }
});
ob_start();
$ok = @class_exists($class) || @interface_exists($class) || @trait_exists($class);
$out = ob_get_clean();
foreach ($errors as $err) {
    fwrite(STDOUT, "DEPRECATION\t" . $class . "\t" . $err . "\n");
}
fwrite(STDOUT, ($ok ? "OK" : "MISSING") . "\t" . $class . "\n");
PHP;

$tmp = tempnam(sys_get_temp_dir(), 'zf1smoke');
file_put_contents($tmp, $childScript);

$results = ['OK' => 0, 'MISSING' => 0, 'FATAL' => 0, 'DEPRECATION' => 0];
$problems = [];

foreach ($slice as $class) {
    $cmd = sprintf(
        '%s %s %s %s 2>&1',
        escapeshellarg(PHP_BINARY),
        escapeshellarg($tmp),
        escapeshellarg($root),
        escapeshellarg($class)
    );
    $output = shell_exec($cmd);
    foreach (explode("\n", trim((string) $output)) as $line) {
        if ($line === '') {
            continue;
        }
        $parts = explode("\t", $line, 3);
        $status = $parts[0];
        if (!isset($results[$status])) {
            // Unexpected output (e.g. a bare fatal not caught by the handler).
            $problems[] = ['UNEXPECTED', $class, $line];
            continue;
        }
        $results[$status]++;
        if ($status === 'FATAL' || $status === 'MISSING' || $status === 'DEPRECATION') {
            $problems[] = [$status, $parts[1] ?? $class, $parts[2] ?? ''];
        }
    }
}

unlink($tmp);

foreach ($problems as [$status, $class, $msg]) {
    printf("%-12s %-58s %s\n", $status, $class, substr($msg, 0, 140));
}

// Machine-readable one-liner so tools/port-status.sh can aggregate a sweep
// without parsing the human-readable problem list.
fwrite(STDOUT, sprintf(
    "SUMMARY\tchecked=%d\tok=%d\tmissing=%d\tfatal=%d\tdeprecations=%d\n",
    count($slice),
    $results['OK'],
    $results['MISSING'],
    $results['FATAL'],
    $results['DEPRECATION']
));

fprintf(
    STDERR,
    "\nchecked %d classes (offset %d, chunk %d): %d ok, %d missing, %d fatal, %d deprecations\n",
    count($slice),
    $offset,
    $chunk,
    $results['OK'],
    $results['MISSING'],
    $results['FATAL'],
    $results['DEPRECATION']
);

exit(($results['FATAL'] + $results['MISSING']) > 0 ? 1 : 0);
