<?php

declare(strict_types=1);

use Rector\Config\RectorConfig;
use Rector\Php84\Rector\Param\ExplicitNullableParamTypeRector;

return RectorConfig::configure()
    ->withPaths([__DIR__ . '/library'])
    ->withSkip([__DIR__ . '/tests', __DIR__ . '/resources'])
    ->withBootstrapFiles([__DIR__ . '/rector-bootstrap.php'])
    ->withAutoloadPaths([__DIR__ . '/library'])
    ->withPhpSets(php83: true)
    ->withRules([
        ExplicitNullableParamTypeRector::class,
    ]);
