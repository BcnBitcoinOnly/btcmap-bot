<?php

declare(strict_types=1);

const LAST_EXEC_FILEPATH = __DIR__ . '/.last_execution_time';

require_once __DIR__ . '/vendor/autoload.php';

if (!extension_loaded('geos')) {
    echo "Missing geos PHP extension.\n";
    echo "Install it from source (https://git.osgeo.org/gitea/geos/php-geos) or apt (sudo apt install php-geos)\n";
    exit(1);
}

if ($argc !== 2 || $argv[1] === '-h') {
    echo "Usage: php bot.php <community>\n";
    exit(1);
}

if (false === ($data = @file_get_contents('https://api.btcmap.org/v2/areas/' . $argv[1]))) {
    echo "Community '$argv[1]' does not exist\n";
    exit(1);
}

$community = json_decode($data);

if (!property_exists($community->tags, 'geo_json')) {
    echo "Community '$argv[1]' does not have GeoJSON data\n";
    exit(1);
}

$communityGeoData = geoPHP::load(json_encode($community->tags->geo_json));

$lastExecution = new DateTimeImmutable(
    file_exists(LAST_EXEC_FILEPATH) ? file_get_contents(LAST_EXEC_FILEPATH) : date('Y-m-d'),
    new DateTimeZone('UTC')
);

$executionTime = (new DateTimeImmutable('UTC'));

$newEvents = json_decode(file_get_contents('https://api.btcmap.org/v2/events?updated_since=' . $lastExecution->format('Y-m-d')));

$relevantEvents = array_filter(
    $newEvents,
    fn($event): bool =>
        $event->type === 'create' &&
        $lastExecution < new DateTimeImmutable($event->created_at) &&
        str_starts_with($event->element_id, 'node:')
);

$newBusinesses = array_map(
    fn($event): stdClass => json_decode(file_get_contents('https://api.btcmap.org/v2/elements/' . $event->element_id)),
    $relevantEvents
);

$newLocalBusinesses = array_filter(
    $newBusinesses,
    fn($business): bool =>
        $communityGeoData->contains(new Point($business->osm_json->lon, $business->osm_json->lat))
);

echo sprintf(
    "Found %d new local businesses in %s since %s\n",
    count($newLocalBusinesses),
    $community->tags->name,
    $lastExecution->format(DateTimeInterface::ATOM)
);

$messages = array_map(
    fn($business): string =>
        sprintf(
            'A new business accepting Bitcoin in %s! %s https://btcmap.org/merchant/%s',
            $community->tags->name,
            $business->osm_json->tags->name,
            $business->id
        ),
    $newLocalBusinesses
);

foreach($messages as $message) {
    exec("noscl publish '$message' > /dev/null");
}

file_put_contents(LAST_EXEC_FILEPATH, $executionTime->format(DateTimeInterface::ATOM));

exit(0);
