# L1 — API Explorer

A small Python script that uses the `requests` library to fetch Pokémon data from the [PokeAPI](https://pokeapi.co/) and print formatted details.

## Files

- `api_explorer.py` — the script
- `requirements.txt` — Python dependency (`requests`)
- `README.md` — this file

## Setup and run

```bash
pip install -r requirements.txt
python api_explorer.py
```

## What it does

For each of `pikachu`, `charizard`, and `bulbasaur`, the script requests `https://pokeapi.co/api/v2/pokemon/<name>`, prints the HTTP status code, and displays the Pokémon's name, height (converted from decimetres to metres), weight (converted from hectograms to kilograms), and types.

It then requests the misspelled `pikacu` to demonstrate error handling: the API returns 404 and the script prints a friendly error instead of crashing.

## Error handling

- All requests go through a shared `make_request()` helper that uses a shared `requests.Session` (so requests reuse one connection), wraps the call in `try/except`, and uses a timeout, so network failures print a message rather than raising.
- An empty or blank name is rejected before any request is sent.
- The status code is checked before the response is used: 404 gets a "not found" message, any other non-200 gets a generic error.
- JSON parsing and field extraction are guarded against malformed responses.
- The returned name is compared against the requested name to verify the API returned the right Pokémon.
