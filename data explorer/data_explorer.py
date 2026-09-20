"""
L10 — Data Explorer
================================
Run with:
    streamlit run data_explorer.py

Fetches and explores user data from JSONPlaceholder.

Features:
    1. Fetch users from https://jsonplaceholder.typicode.com/users
       using @st.cache_data(ttl=300)
    2. Display 3 metrics: total users, most common city, avg latitude
    3. Sidebar filters: name text_input, city multiselect, latitude range
    4. st.dataframe() showing the filtered users
    5. st.bar_chart() showing users per city for the current filter

Key concepts:
    @st.cache_data(ttl=300)
        → Caches the function's return value.
        → Re-runs only when inputs change or after 300 seconds.
        → Without it, the API is called on EVERY widget interaction.

    st.dataframe()  — interactive, sortable table
    st.table()      — static, non-interactive table (better for small data)

    st.metric(label, value, delta, delta_color)
        delta_color:
            "normal"  — green if positive, red if negative (default)
            "inverse" — red if positive, green if negative
            "off"     — neutral grey regardless of sign
"""

import math

import requests
import streamlit as st

API_BASE = "https://jsonplaceholder.typicode.com"
USERS_ENDPOINT = f"{API_BASE}/users"
REQUEST_TIMEOUT = 10


# ── Shared request helper ──────────────────────────────────────────────────
class ApiError(Exception):
    """Any failure reaching or reading the API, with a message fit to display."""


def api_get(path, params=None, timeout=REQUEST_TIMEOUT, expect=list):
    """GET `path` from the API and return the decoded JSON.

    One place for every outbound request, so timeouts, status-code checks,
    JSON decoding and shape validation are handled identically no matter
    which endpoint is being called.

    Args:
        path:    absolute URL, or a path like "/users" joined onto API_BASE.
        params:  optional query-string dict.
        timeout: seconds to wait before giving up.
        expect:  the type the decoded payload must be (list or dict), or
                 None to skip the shape check.

    Raises:
        ApiError: on timeout, connection failure, 4xx/5xx status, undecodable
                  JSON, or a payload that is not the expected type.
    """
    url = path if path.startswith("http") else f"{API_BASE}{path}"

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()  # raises for 4xx/5xx
    except requests.exceptions.Timeout as exc:
        raise ApiError(f"The request to {url} timed out after {timeout}s.") from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise ApiError(f"The API returned HTTP {status}. Try again in a moment.") from exc
    except requests.exceptions.RequestException as exc:
        raise ApiError(f"Could not reach the API: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError("The API response was not valid JSON.") from exc

    if expect is not None and not isinstance(payload, expect):
        raise ApiError(
            f"Expected {expect.__name__} data from {url}, "
            f"got {type(payload).__name__}."
        )
    return payload


# ── Step 2: Cached data fetch ──────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_users():
    """Return the user list, cached for 300 seconds.

    Widget interactions (typing in a filter, sorting the table) re-run the
    script but reuse this cached value instead of re-hitting the API.
    Raises ApiError, which the caller turns into a friendly message.
    """
    return api_get("/users", expect=list)


# ── Step 1: Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Explorer",
    page_icon="🔎",
    layout="wide",
)


# ── Helpers ────────────────────────────────────────────────────────────────
def get_city(user):
    """City for a user, or 'Unknown' if the field is missing/blank."""
    city = (user.get("address") or {}).get("city")
    return city.strip() if isinstance(city, str) and city.strip() else "Unknown"


def get_lat(user):
    """Latitude as a float, or None if missing or not numeric.

    The API nests geo under address; a top-level "geo" key is also accepted
    so the function survives either shape.
    """
    geo = (user.get("address") or {}).get("geo") or user.get("geo") or {}
    try:
        return float(geo.get("lat"))
    except (TypeError, ValueError):
        return None


def get_company(user):
    """Company name, or an em dash if absent."""
    name = (user.get("company") or {}).get("name")
    return name if name else "—"


def count_by_city(user_list):
    """Map city name -> number of users in it."""
    counts = {}
    for user in user_list:
        city = get_city(user)
        counts[city] = counts.get(city, 0) + 1
    return counts


# ── Step 3: Load data ──────────────────────────────────────────────────────
with st.spinner("Fetching users…"):
    try:
        users = fetch_users()
    except ApiError as exc:
        st.error(str(exc))
        st.button("🔄 Retry", on_click=fetch_users.clear)
        st.stop()

if not users:
    st.title("🔎 Data Explorer")
    st.warning("The API returned no users, so there is nothing to explore.")
    st.button("🔄 Refresh data", on_click=fetch_users.clear)
    st.stop()


# ── Step 4: Derived metrics (always across ALL users) ──────────────────────
total_users = len(users)

city_counts = count_by_city(users)

# Sorting by (-count, name) makes the winner deterministic: highest count
# first, then alphabetical, instead of whatever order the API returned.
most_common_city = min(city_counts, key=lambda city: (-city_counts[city], city))
top_count = city_counts[most_common_city]
tied_cities = sum(1 for count in city_counts.values() if count == top_count)

latitudes = [lat for lat in (get_lat(user) for user in users) if lat is not None]
avg_lat = sum(latitudes) / len(latitudes) if latitudes else None


# ── Step 5: Page title ────────────────────────────────────────────────────
st.title("🔎 Data Explorer")
st.caption("Live user data from JSONPlaceholder, cached for 5 minutes.")


# ── Step 6: Metrics row ───────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("👥 Total Users", total_users)

with col2:
    if tied_cities > 1:
        city_delta = f"{top_count} user(s) — tied with {tied_cities - 1} other city/cities"
    else:
        city_delta = f"{top_count} user(s)"
    st.metric(
        "🏙️ Most Common City",
        most_common_city,
        delta=city_delta,
        delta_color="off",  # a city name has no good/bad direction
    )

with col3:
    if avg_lat is None:
        st.metric("🌍 Avg. Latitude", "N/A", delta="no usable coordinates", delta_color="off")
    else:
        hemisphere = "Northern" if avg_lat >= 0 else "Southern"
        st.metric(
            "🌍 Avg. Latitude",
            f"{avg_lat:.2f}°",
            delta=f"{hemisphere} hemisphere",
            delta_color="off",
        )


# ── Step 7: Sidebar filters ───────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    name_filter = st.text_input(
        "Filter by name",
        placeholder="e.g. Leanne",
        help="Case-insensitive match on any part of the name.",
    )

    selected_cities = st.multiselect(
        "Filter by city",
        options=sorted(city_counts),
        help="Leave empty to include every city.",
    )

    # A slider needs two distinct bounds, so it only appears when the data
    # actually spans a range of latitudes.
    lat_range = None
    if len(latitudes) >= 2 and min(latitudes) < max(latitudes):
        # Round outward, never inward: rounding the floor up would silently
        # exclude the southernmost user the moment the slider is touched.
        lat_floor = math.floor(min(latitudes) * 100) / 100
        lat_ceiling = math.ceil(max(latitudes) * 100) / 100
        lat_range = st.slider(
            "Latitude range",
            min_value=lat_floor,
            max_value=lat_ceiling,
            value=(lat_floor, lat_ceiling),
            step=0.01,
            help="Users with no usable coordinates drop out once you narrow this.",
        )
        if lat_range == (lat_floor, lat_ceiling):
            lat_range = None  # full span means "no latitude filter"

    st.divider()
    st.caption("Data is cached for 5 minutes.")
    refresh = st.button(
        "🔄 Refresh data",
        help="Clear the cache and fetch from the API again.",
        width="stretch",
    )
    if refresh:
        fetch_users.clear()
        st.rerun()


# ── Apply the filters ─────────────────────────────────────────────────────
filtered_users = users

query = name_filter.strip().lower()
if query:
    filtered_users = [u for u in filtered_users if query in (u.get("name") or "").lower()]

if selected_cities:
    wanted = set(selected_cities)
    filtered_users = [u for u in filtered_users if get_city(u) in wanted]

if lat_range is not None:
    low, high = lat_range
    filtered_users = [
        u for u in filtered_users
        if (lat := get_lat(u)) is not None and low <= lat <= high
    ]

active_filters = []
if query:
    active_filters.append(f"name contains “{name_filter.strip()}”")
if selected_cities:
    active_filters.append(f"city in {', '.join(sorted(selected_cities))}")
if lat_range is not None:
    active_filters.append(f"latitude {lat_range[0]:.2f}° to {lat_range[1]:.2f}°")


# ── Step 8: Data table ────────────────────────────────────────────────────
st.subheader("Users")

table_rows = [
    {
        "Name": user.get("name") or "—",
        "Email": user.get("email") or "—",
        "City": get_city(user),
        "Company": get_company(user),
    }
    for user in filtered_users
]

if table_rows:
    st.caption(f"Showing {len(table_rows)} of {total_users} users.")
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
else:
    st.info(
        "No users match the current filters "
        f"({'; '.join(active_filters)}). Clear them to see all {total_users}."
    )


# ── Step 9: Bar chart ─────────────────────────────────────────────────────
st.subheader("Users per City")

filtered_city_counts = count_by_city(filtered_users)

if filtered_city_counts:
    st.bar_chart(filtered_city_counts)
    if active_filters:
        st.caption(
            f"Chart reflects the current filters: {'; '.join(active_filters)}."
        )
    else:
        st.caption("Chart covers all users. Narrow the sidebar filters to focus it.")
else:
    st.caption("Nothing to chart — no users match the current filters.")
