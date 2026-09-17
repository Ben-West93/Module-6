"""
L1 — API Explorer
=================
Uses the `requests` library to fetch data from the PokeAPI and print nicely
formatted Pokémon info.

Key concepts used:
- requests.get(url)       : sends an HTTP GET request
- response.status_code    : the HTTP status code (200 = OK, 404 = Not Found)
- response.json()         : parses the JSON response body into a Python dict

Run:
    python api_explorer.py
"""

from typing import Optional

import requests

# ── Base URL ──────────────────────────────────────────────────────────────────
# Append a Pokémon name to this URL to build the full endpoint.
# Example: BASE_URL + "pikachu"  →  "https://pokeapi.co/api/v2/pokemon/pikachu"
BASE_URL = "https://pokeapi.co/api/v2/pokemon/"
TIMEOUT_SECONDS = 10

# PokeAPI unit conversions
DECIMETRES_PER_METRE = 10   # height is returned in decimetres
HECTOGRAMS_PER_KG = 10      # weight is returned in hectograms

# One shared session so all requests reuse the same connection
session = requests.Session()


def make_request(url: str) -> Optional[requests.Response]:
    """Shared request helper: sends a GET request and returns the response,
    or None if a network-level error occurred (timeout, no connection, etc.)."""
    try:
        return session.get(url, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        print(f"  Error: request timed out after {TIMEOUT_SECONDS}s.")
    except requests.exceptions.ConnectionError:
        print("  Error: could not connect to the API. Check your internet connection.")
    except requests.exceptions.RequestException as exc:
        print(f"  Error: request failed ({exc}).")
    return None


def fetch_pokemon(name: str) -> None:
    """Fetch and print details for a single Pokémon by name."""

    print(f"\n{'=' * 40}")
    print(f"  Fetching: {name}")
    print(f"{'=' * 40}")

    # Normalize the name once so the URL and the verification check match
    normalized = name.strip().lower()
    if not normalized:
        print("  Error: no Pokémon name was provided.")
        return

    # Build the full URL by combining BASE_URL and the pokemon name
    url = BASE_URL + normalized

    # Send a GET request (via the shared helper, wrapped in try/except)
    response = make_request(url)
    if response is None:
        return

    # Print the status code so we can see what the API returned
    print(f"  Status code: {response.status_code}")

    # 404 → friendly error message, return early
    if response.status_code == 404:
        print(f"  Error: Pokémon '{name}' not found. Check the spelling and try again.")
        return

    # Any other non-200 → generic error, return early
    if response.status_code != 200:
        print(f"  Error: unexpected response from the API (status {response.status_code}).")
        return

    # Parse the JSON response body
    try:
        data = response.json()
    except ValueError:
        print("  Error: the API response was not valid JSON.")
        return

    # Extract name, height, and weight
    try:
        poke_name = data["name"]
        height = data["height"]
        weight = data["weight"]

        # Extract the list of type names
        types = [entry["type"]["name"] for entry in data["types"]]
    except (KeyError, TypeError) as exc:
        print(f"  Error: response was missing expected data ({exc}).")
        return

    # Verify the API returned the Pokémon we actually asked for
    if poke_name != normalized:
        print(f"  Warning: requested '{name}' but API returned '{poke_name}'.")

    # Print name, height (metres), weight (kg), and types
    # Height is in decimetres, weight is in hectograms → convert with the constants above
    print(f"  Name:   {poke_name.capitalize()}")
    print(f"  Height: {height / DECIMETRES_PER_METRE:.1f} m")
    print(f"  Weight: {weight / HECTOGRAMS_PER_KG:.1f} kg")
    print(f"  Types:  {', '.join(t.capitalize() for t in types)}")


def main():
    print("=" * 40)
    print("  Pokémon API Explorer")
    print("=" * 40)

    # Fetch the three valid Pokémon
    for name in ["pikachu", "charizard", "bulbasaur"]:
        fetch_pokemon(name)

    # Misspelled name to test 404 error handling
    fetch_pokemon("pikacu")

    print("\nDone!\n")


if __name__ == "__main__":
    main()
