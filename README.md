# BTCMAP Bot for Nostr

A bot that leverages the https://btcmap.org/ API to post a Nostr note whenever a local business starts accepting Bitcoin in your area.

A project brought to you by the [Barcelona Bitcoin Only](https://twitter.com/BcnBitcoinOnly) community.

## Requirements

* Python +3.10
* [Poetry](https://python-poetry.org/docs/)
* [noscl](https://github.com/fiatjaf/noscl), install it with `go install github.com/fiatjaf/noscl@latest` and make sure it is on your PATH. Requires the [Go toolchain](https://go.dev)

## Setup

1. Clone the project and install project dependencies and virtualenv with poetry: `poetry install`
2. Find your community on the BTC Map and take note of its name on the URL. For instance, for the [BBO Community](https://btcmap.org/community/barcelona-bitcoin-only) it would be `barcelona-bitcoin-only`
3. Generate a new Nostr identity with noscl:
    ```bash
    $ noscl key-gen
    seed: wheat arrange shoulder number torch bone old stairs flat slow resemble hungry treat hood valve six permit cotton grunt profit latin try certain episode
    private key: 057a88cb9192f55ef744944cbc4cfbbdefc2f81ef89b060e46eb7872e895dfd5
    ```
4. Set that key as your identity for noscl:
    ```bash
    $ noscl setprivate 057a88cb9192f55ef744944cbc4cfbbdefc2f81ef89b060e46eb7872e895dfd5
    ```
5. Register a few relays:
    ```bash
    $ noscl relay add wss://nos.lol
    $ noscl relay add wss://nostr.bitcoiner.social
    $ noscl relay add wss://nostr.mom
    $ noscl relay add wss://nostr.mutinywallet.com
    ```
6. Run the bot passing your community identifier as its first and only argument:
    ```bash
    $ poetry run python bot.py einundzwanzig-koeln
    Found 1 new local businesses in Einundzwanzig Köln since 2023-05-19T00:00:00+00:00
    ```
7. Find out your public key with `noscl public`, then convert it into npub format with https://nostrtool.com/ and search for the notes with your favorite Nostr client (or debug with https://nostr.guru).
8. Once everything works, automate the bot execution at your desired frequency with [cron](https://crontab.guru/).

## Roadmap

* Multi-language support.
* Other settings.
