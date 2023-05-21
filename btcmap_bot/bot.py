from datetime import datetime
from datetime import timezone
from pathlib import Path
import json
import requests
import shapely.geometry
import subprocess
import sys


def run(community_name):
    # TODO convert to constant
    LAST_EXEC_FILEPATH = str(Path(__file__).parent.parent) + '/.last_execution_time'

    execution_time = datetime.now(timezone.utc)

    community = requests.get(f'https://api.btcmap.org/v2/areas/{community_name}')

    if community.status_code != 200:
        print(f'Community {community_name}  does not exist')
        exit(1)

    community = json.loads(community.content)

    if 'geo_json' not in community['tags']:
        print(f'Community {community_name} does not have GeoJSON data')
        exit(1)

    community_geo_json = shapely.geometry.shape(community['tags']['geo_json'])

    new_events = json.loads(requests.get('https://api.btcmap.org/v2/events?updated_since=2023-05-19').content)

    # TODO also filter by last execution time
    relevant_events = [
        event
        for event in new_events
        if event['type'] == 'create' and event['element_id'].startswith('node:')
    ]

    new_businesses = [
        json.loads(requests.get(f'https://api.btcmap.org/v2/elements/{event["element_id"]}').content)
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

    print('Found {} new local businesses in {} since whatever'.format(
        len(new_local_businesses),
        community['tags']['name'])
    )

    nostr_messages = [
        'A new business accepting Bitcoin in {}! {} https://btcmap.org/merchant/{}'.format(
            community['tags']['name'],
            business['osm_json']['tags']['name'],
            business['id']
        )
        for business in new_local_businesses
    ]

    # TODO supress stdout
    for message in nostr_messages:
        subprocess.run(['noscl', 'publish', f"'{message}'"])


run(sys.argv[1])
