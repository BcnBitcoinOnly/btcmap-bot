# New bitcoin business bot

## What is this

Simple spec for a bot that alerts of new businesses appearing in a specific area in btcmap.org.


## Requirements

Behaviour:
- The bot publishes nostr notes under a specified identity. 
- The notes report on new businesses appearing in a specific area in btcmap.org. Every time a new business appears, the bot publishes an event.
- The bot only sends a note once per new business appearing.

A few basic technical requirements:
- Whole thing should be runnable on any Linux machine.
- As stateless as possible to reduce hosting and deployment headaches.


## Design

The bot has two main components: a script to spot new businesses (spotter) and a script to publish them to nostr (publisher).

### Spotter

The script is responsible for:
- Reading config and last_execution time
- Interacting with the btcmap.org API.
- Filtering the responses from btcmap.org to keep only the new businesses.
- Compose the messages to be sent as nostr notes and save them

You can find below a pseudo-codish idea on the steps the script should follow:

```
config = read_config_file(path_to_config_file)
last_execution_datetime = read_last_execution_datetime(
    config.last_execution_datetime_file_path
)

# Request Area endpoint and fetch geojson
# Example: https://api.btcmap.org/v2/areas/barcelona-bitcoin-only
# Geojson is in path $.tags.geo_json
relevant_area_geojson = fetch_area_from_community_name(config.community_name)

# Request events since last execution time
# Example: https://api.btcmap.org/v2/events?updated_since=2023-04-01
# Time precision filtering can't be done in the btcmap API, so the function
# should first do date-level filtering when calling the API and after filter
# the received events by time as well.
all_events_since_last_date = fetch_events_after_date(last_execution_datetime)


# Filter out events to keep those with `type = "create"`.
all_create_events_since_last_date = filter_events(
    events=all_events_since_last_date,
    types_to_keep=["create"]
)


# So far we have worked with events. But it's businesses (or nodes, in OSM
# lingo) that we are actually interested in. From each create event we can
# fetch a node ID that we can use to retrieve the details of the node. So,
# with this, we jump from a list of create events to a list of created nodes.
# Example: https://api.btcmap.org/v2/elements/node:10776994043
# 
# The elements endpoint will already provide us with the coordiantes of the
# node. For efficiency, it makes sense to throw away nodes outside of our
# area of interest on the spot. There's probably some library implementing 
# geographical logic and data structures that can read the GeoJSON and check 
# if the coordinates are inside the relevant area.
# The coordinates are found in the path: $.osm_json.lat and $.osm_json.lon
all_new_nodes_in_area = fetch_newly_created_nodes_in_area(
    create_events=all_create_events_since_last_date,
	area_geojson=relevant_area_geojson
)

# We finally have the new businesses. To finish up, we go from the 
# structured info of the business to a human readable message that we save
# to disk for the publisher script to actually push to the relays.
# This is a creative bit but also a challenging one because OSM tags have a
# very flexible schema. For a first version, I think it should be enough to
# make a simple text with the name of the business and the URL to its btcmap
# page.
# Example: A new business accepting Bitcoin in Barcelona! Faire: Brunch & Drinks
# https://btcmap.org/merchant/node:10179182694
#
# The name can be found in the path $.osm_json.tags.name. The id in $.id.
new_business_messages = compose_messages_from_nodes(all_new_nodes_in_area)

# Finally, save this to disk. This could be a path where each different message
# gets stored as a single A simple JSON should do the trick.
persist_messages_to_post(new_business_messages)

```

### Publisher

The publisher is responsible for:
- Checking if there are pending messages to publish.
- Connecting to relays and sending the messages.

I've hacked together the below example by using the docs of the [python-nostr](https://github.com/jeffthibault/python-nostr) package, but I think the idea is clear enough to be ported to any language.

```python
import json 
import ssl
import time
from nostr.event import Event
from nostr.relay_manager import RelayManager
from nostr.message_type import ClientMessageType
from nostr.key import PrivateKey

relays_to_use = load_relay_list() # Here we should load the chosen relays from the config file

relay_manager = RelayManager()
for relay in relays_to_use:
	relay_manager.add_relay(relay)
relay_manager.open_connections({"cert_reqs": ssl.CERT_NONE})
time.sleep(5)

private_key = load_private_keys() # Here we should load the nsec from the config file

messages_to_send = load_messages() # Here we shoud load the messages persisted by the Spotter

for message in messages_to_send:
	event = Event(message)
	private_key.sign_event(event)
	relay_manager.publish_event(event)

time.sleep(5) # allow the messages to send

relay_manager.close_connections()

# Some extra code to delete the message files created by the Spotter since they are not needed anymore
```

### Config file

You can find below the proposed config file schema:

```json
{
	"community_name": "barcelona-bitcoin-only",
	"last_execution_datetime_file_path": "./last_execution_datetime",
	"message_storage_path": "./messages_to_send/",
	"relays": [
		"wss://nostr-pub.wellorder.net",
		"wss://relay.damus.io",
		"... and all the other relays we want to send to."
	],
	"nsec": "the nsec for the bot goes here."
}
```

Besides that, a simple text files stores that last time the spotter 

## Deployment and monitoring

Quite simple:
1. Create a nostr identity and gear it up so it looks cool.
2. Clone the scripts on any linux server.
3. Fill in a config file with the necessary details.
4. Generate the file with the last execution datetime and fill it. It probably makes sense to place the current datetime.
5. Set up cron entries to execute the Spotter and Publisher scripts at regular intervals.

To keep lights on:
- Check the bot here and there to see if it's posting messages (a bit tricky if the area it monitors doesn't have a lot of activity).
- Review regularly relay list to see if any relays should be removed or added.
- Backup the folder where everything lives by copying it somewhere else. 
