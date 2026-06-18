"""
Layer 3 (Prescription) routing pieces. Direct ports of haversine_km,
nearest_corridor_to_point, officer_eta_minutes, nearest_police_stations_by_time,
and find_safe_route (the Proposer/Adversary loop) from the notebook.
find_safe_route is now backed by find_safe_route_stream, a generator that
yields one event per candidate path evaluated; find_safe_route just
consumes its own generator and returns the final result, so behavior is
unchanged for existing callers.
"""
import math

import networkx as nx
import pandas as pd

from .data_loader import data
from .simulation import build_travel_time_graph


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_corridor_to_point(lat, lon):
    dists = data.corridor_centroids.copy()
    dists["dist_km"] = dists.apply(lambda r: haversine_km(lat, lon, r["latitude"], r["longitude"]), axis=1)
    nearest = dists.sort_values("dist_km").iloc[0]
    return nearest["corridor"], nearest["dist_km"]


def officer_eta_minutes(station_row, target_corridor, G_time):
    station_corridor, access_dist_km = nearest_corridor_to_point(station_row["latitude"], station_row["longitude"])
    access_time_min = (access_dist_km / data.bpr_params["local_access_speed_kmph"]) * 60

    if station_corridor == target_corridor:
        graph_time_min = 0.0
    else:
        try:
            graph_time_min = nx.shortest_path_length(G_time, station_corridor, target_corridor, weight="weight")
        except nx.NetworkXNoPath:
            graph_time_min = float("inf")

    return access_time_min + graph_time_min, station_corridor


def nearest_police_stations_by_time(corridor_name, G_time, n=3):
    rows = []
    for _, station in data.station_locations.iterrows():
        eta, entry_corridor = officer_eta_minutes(station, corridor_name, G_time)
        rows.append(
            {"police_station": station["police_station"], "eta_minutes": round(eta, 1), "entry_corridor": entry_corridor}
        )
    return pd.DataFrame(rows).sort_values("eta_minutes").head(n)


def find_safe_route_stream(origin, destination, network_state_df, blocked_corridors, k=5, red_threshold=0.9, max_attempts=10):
    """Generator version of find_safe_route -- yields one 'log' event per
    candidate path the Proposer/Adversary loop evaluates, then a final
    'result' event carrying the same dict find_safe_route returns."""
    G_search = build_travel_time_graph(network_state_df)
    for b in blocked_corridors:
        if b in G_search:
            G_search.remove_node(b)

    vc_lookup = network_state_df.set_index("corridor")["vc_ratio"].to_dict()
    negotiation_log = []

    if origin not in G_search or destination not in G_search:
        result = {
            "status": "NO_PATH", "path": None, "bottleneck": None, "bottleneck_vc": None,
            "eta_minutes": None, "negotiation_log": ["Origin or destination is blocked/unreachable."],
        }
        yield {"type": "log", "stage": "route", "message": result["negotiation_log"][0]}
        yield {"type": "result", "stage": "route", "data": result}
        return

    try:
        path_generator = nx.shortest_simple_paths(G_search, origin, destination, weight="weight")
    except nx.NetworkXNoPath:
        result = {
            "status": "NO_PATH", "path": None, "bottleneck": None, "bottleneck_vc": None,
            "eta_minutes": None, "negotiation_log": ["No path exists between origin and destination."],
        }
        yield {"type": "log", "stage": "route", "message": result["negotiation_log"][0]}
        yield {"type": "result", "stage": "route", "data": result}
        return

    best_available = None
    attempts = 0
    for path in path_generator:
        attempts += 1
        if attempts > max_attempts:
            break

        path_vcs = {node: vc_lookup.get(node, 0) for node in path}
        bottleneck = max(path_vcs, key=path_vcs.get)
        bottleneck_vc = path_vcs[bottleneck]
        eta = nx.path_weight(G_search, path, weight="weight")

        if bottleneck_vc < red_threshold:
            msg = f"Proposer suggests {' -> '.join(path)}. Adversary: ACCEPTED ({bottleneck} at {bottleneck_vc:.2f} V/C)."
            negotiation_log.append(msg)
            yield {"type": "log", "stage": "route", "message": msg}
            result = {
                "status": "CLEAN", "path": path, "bottleneck": bottleneck, "bottleneck_vc": round(bottleneck_vc, 3),
                "eta_minutes": round(eta, 1), "negotiation_log": negotiation_log,
            }
            yield {"type": "result", "stage": "route", "data": result}
            return
        else:
            msg = (
                f"Proposer suggests {' -> '.join(path)}. Adversary: REJECTED "
                f"({bottleneck} at {bottleneck_vc:.2f} V/C exceeds {red_threshold})."
            )
            negotiation_log.append(msg)
            yield {"type": "log", "stage": "route", "message": msg}
            if best_available is None or bottleneck_vc < best_available["bottleneck_vc"]:
                best_available = {"path": path, "bottleneck": bottleneck, "bottleneck_vc": bottleneck_vc, "eta_minutes": eta}

    if best_available:
        msg = f"No clean path found after {attempts} attempts. Falling back to best available."
        negotiation_log.append(msg)
        yield {"type": "log", "stage": "route", "message": msg}
        result = {
            "status": "BEST_AVAILABLE", "path": best_available["path"], "bottleneck": best_available["bottleneck"],
            "bottleneck_vc": round(best_available["bottleneck_vc"], 3),
            "eta_minutes": round(best_available["eta_minutes"], 1), "negotiation_log": negotiation_log,
        }
        yield {"type": "result", "stage": "route", "data": result}
        return

    msg = "All candidate paths exhausted with no viable route."
    yield {"type": "log", "stage": "route", "message": msg}
    result = {
        "status": "NO_PATH", "path": None, "bottleneck": None, "bottleneck_vc": None, "eta_minutes": None,
        "negotiation_log": negotiation_log + [msg],
    }
    yield {"type": "result", "stage": "route", "data": result}


def find_safe_route(origin, destination, network_state_df, blocked_corridors, k=5, red_threshold=0.9, max_attempts=10):
    """Same computation as find_safe_route_stream, collected into the
    single return value the existing /route and /playbook endpoints
    expect."""
    result = None
    for event in find_safe_route_stream(origin, destination, network_state_df, blocked_corridors, k, red_threshold, max_attempts):
        if event["type"] == "result":
            result = event["data"]
    return result