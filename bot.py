from datetime import datetime, time
from datetime import timezone
from pathlib import Path
import json
import requests
import shapely.geometry
import subprocess
import sys

LAST_EXEC_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
LAST_EXEC_FILEPATH = Path(__file__).parent / '.last_execution_time'
BTCMAP_ROOT_URL = "https://api.btcmap.org"
BTCMAP_API_VERSION = "v2"


def invoke_noscl(message: str) -> int:
    return subprocess.run(['noscl', 'publish', message], stdout=subprocess.DEVNULL).returncode


def main(community_name: str) -> None:
    execution_time = datetime.now(timezone.utc)
    try:
        last_execution_time = datetime.strptime(LAST_EXEC_FILEPATH.read_text().strip(), LAST_EXEC_DATETIME_FORMAT)
    except FileNotFoundError:
        last_execution_time = datetime.combine(date=datetime.today(), time=time(hour=0, minute=0, second=0))

    community_response = requests.get(f'{BTCMAP_ROOT_URL}/{BTCMAP_API_VERSION}/areas/{community_name}')

    if community_response.status_code != 200:
        print(f'Community {community_name} does not exist.')
        exit(1)

    community = json.loads(community_response.content)

    if 'geo_json' not in community['tags']:
        print(f'Community {community_name} does not have GeoJSON data.')
        exit(1)

    community_geo_json = shapely.geometry.shape(community['tags']['geo_json'])

    new_events = json.loads(requests.get(
        f"{BTCMAP_ROOT_URL}/{BTCMAP_API_VERSION}/events?updated_since={last_execution_time.strftime('%Y-%m-%d')}"
    ).content)

    event_is_of_type_create = lambda event: event['type'] == 'create'
    element_id_starts_with_node = lambda event: event['element_id'].startswith('node:')
    created_after_last_script_execution_time = lambda event: last_execution_time < datetime.strptime(event['created_at'], LAST_EXEC_DATETIME_FORMAT)

    relevant_events = [
        event
        for event in new_events
        if event_is_of_type_create(event) and
        element_id_starts_with_node(event) and
        created_after_last_script_execution_time
    ]

    new_businesses = [
        json.loads(requests.get(f'{BTCMAP_ROOT_URL}/{BTCMAP_API_VERSION}/elements/{event["element_id"]}').content)
        for event in relevant_events
    ]

    new_local_businesses = [
        business
        for business in new_businesses
        if shapely.contains(
            community_geo_json,
            shapely.geometry.Point(business['osm_json']['lon'], business['osm_json']['lat'])
        )
    ]

    nostr_messages = [
        'A new business accepting Bitcoin in {}! {} https://btcmap.org/merchant/{}'.format(
            community['tags']['name'],
            business['osm_json']['tags']['name'],
            business['id']
        )
        for business in new_local_businesses
    ]

    print('Found {} new local businesses in {} since {}.'.format(
        len(nostr_messages),
        community['tags']['name'],
        last_execution_time.isoformat()
    )
    )

    save_state = True
    for message in nostr_messages:
        max_retries = 3
        while max_retries > 0 and invoke_noscl(message) != 0:
            max_retries -= 1

        if max_retries == 0:
            save_state = False

    if save_state:
        with open(LAST_EXEC_FILEPATH, 'w') as fp:
            fp.write(execution_time.strftime(LAST_EXEC_DATETIME_FORMAT))


if __name__ == '__main__':
    main(sys.argv[1])
