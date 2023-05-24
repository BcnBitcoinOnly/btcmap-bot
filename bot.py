from datetime import datetime
from datetime import timezone
from pathlib import Path
import json
import requests
import shapely.geometry
import subprocess
import sys

FUCKY_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
LAST_EXEC_FILEPATH = str(Path(__file__).parent) + '/.last_execution_time'


def invoke_noscl(message: str) -> int:
    return subprocess.run(['noscl', 'publish', message], stdout=subprocess.DEVNULL).returncode


def main(community_name: str) -> None:
    execution_time = datetime.now(timezone.utc)
    last_execution_time = datetime.strptime(Path(LAST_EXEC_FILEPATH).read_text().strip(), FUCKY_FORMAT)

    community = requests.get(f'https://api.btcmap.org/v2/areas/{community_name}')

    if community.status_code != 200:
        print(f'Community {community_name}  does not exist')
        exit(1)

    community = json.loads(community.content)

    if 'geo_json' not in community['tags']:
        print(f'Community {community_name} does not have GeoJSON data')
        exit(1)

    community_geo_json = shapely.geometry.shape(community['tags']['geo_json'])

    nostr_messages = [
        'A new business accepting Bitcoin in {}! {} https://btcmap.org/merchant/{}'.format(
            community['tags']['name'],
            business['osm_json']['tags']['name'],
            business['id']
        )
        for business in [
            json.loads(requests.get(f'https://api.btcmap.org/v2/elements/{event["element_id"]}').content)
            for event in [
                event
                for event in json.loads(requests.get(
                    'https://api.btcmap.org/v2/events?updated_since=' + last_execution_time.strftime('%Y-%m-%d')
                ).content)
                if event['type'] == 'create' and
                event['element_id'].startswith('node:') and
                last_execution_time < datetime.strptime(event['created_at'], FUCKY_FORMAT)
            ]
        ]
        if shapely.contains(
            community_geo_json,
            shapely.geometry.Point(business['osm_json']['lon'], business['osm_json']['lat'])
        )
    ]

    print('Found {} new local businesses in {} since whatever'.format(
        len(nostr_messages),
        community['tags']['name'])
    )

    save_state = True
    for message in nostr_messages:
        maxretries = 3
        while maxretries > 0 and invoke_noscl(message) != 0:
            maxretries -= 1

        if maxretries == 0:
            save_state = False

    if save_state:
        with open(LAST_EXEC_FILEPATH, 'w') as fp:
            fp.write(execution_time.strftime(FUCKY_FORMAT))


if __name__ == "__main__":
    main(sys.argv[1])
