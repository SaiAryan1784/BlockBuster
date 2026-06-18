"""
Layer 2 (Simulation). Direct ports of get_demand / get_color / inject_disaster
/ the BPR travel-time functions / build_travel_time_graph / stress_test_plan
from the notebook. No logic changes from what was validated in Colab --
inject_disaster and stress_test_plan are now backed by generator versions
(inject_disaster_stream, stress_test_plan_stream) so the live negotiation
feed can stream real progress; the original functions just consume their
own generator and return the final result, so behavior is unchanged.
"""
import networkx as nx
import pandas as pd

from .data_loader import data


def get_demand(corridor: str, hour: int) -> float:
    diurnal = data.diurnal_factor[hour]
    share = data.demand_share_compressed[corridor]
    return diurnal * share * data.peak_demand_scale


def get_color(vc: float) -> str:
    if vc < 0.7:
        return "green"
    elif vc < 0.9:
        return "yellow"
    return "red"


def free_flow_time_min(distance_km: float, speed_kmph: float = None) -> float:
    speed = speed_kmph or data.bpr_params["free_flow_speed_kmph"]
    return (distance_km / speed) * 60


def bpr_travel_time_min(distance_km: float, vc_ratio: float) -> float:
    p = data.bpr_params
    fft = free_flow_time_min(distance_km, p["free_flow_speed_kmph"])
    vc_capped = 5.0 if vc_ratio == float("inf") else min(vc_ratio, 5.0)
    return fft * (1 + p["alpha"] * (vc_capped ** p["beta"]))


def inject_disaster_stream(target_corridors, hour, capacity_remaining_pct=0.0, max_iterations=10, protect=None):
    """Generator version of inject_disaster -- yields one 'log' event per
    redistribution iteration, then a final 'result' event carrying the
    same (state_df, spillover_received, unresolved) data inject_disaster
    returns. This is the single source of truth; inject_disaster below
    just consumes this generator."""
    if protect is None:
        protect = []
    if isinstance(target_corridors, str):
        target_corridors = [target_corridors]

    disrupted_capacity = dict(data.capacity)
    demand_state = {c: get_demand(c, hour) for c in data.corridors}
    spillover_received = {c: 0.0 for c in data.corridors}

    excess = {c: 0.0 for c in data.corridors}
    for target in target_corridors:
        disrupted_capacity[target] = data.capacity[target] * capacity_remaining_pct
        excess[target] = max(demand_state[target] - disrupted_capacity[target], 0)
        demand_state[target] = min(demand_state[target], disrupted_capacity[target])

    initial_excess = sum(excess.values())
    yield {
        "type": "log",
        "stage": "inject_disaster",
        "message": f"Disaster injected on {', '.join(target_corridors)} at hour {hour}. "
                   f"Initial excess demand to redistribute: {initial_excess:.1f} veh/hr.",
    }

    for i in range(max_iterations):
        iteration_count = i + 1
        if sum(excess.values()) < 1.0:
            break
        additions = {c: 0.0 for c in data.corridors}
        for c, exc in excess.items():
            if exc <= 1e-6:
                continue
            neighbors = [n for n in data.G_sim.neighbors(c) if n not in protect]
            if not neighbors:
                neighbors = list(data.G_sim.neighbors(c))
            weights = {
                n: max(disrupted_capacity[n] - demand_state[n], 1.0) / data.G_sim[c][n]["weight"]
                for n in neighbors
            }
            total_weight = sum(weights.values())
            for n, w in weights.items():
                additions[n] += exc * (w / total_weight)

        new_excess = {c: 0.0 for c in data.corridors}
        for c in data.corridors:
            demand_state[c] += additions[c]
            spillover_received[c] += additions[c]
            if demand_state[c] > disrupted_capacity[c]:
                new_excess[c] = demand_state[c] - disrupted_capacity[c]
                demand_state[c] = disrupted_capacity[c]
        excess = new_excess

        remaining = sum(excess.values())
        yield {
            "type": "log",
            "stage": "inject_disaster",
            "message": f"Iteration {iteration_count}: redistributed spillover across the network. "
                       f"Unresolved excess remaining: {remaining:.1f} veh/hr.",
        }

    unresolved = sum(excess.values())
    rows = []
    for c in data.corridors:
        cap, demand = disrupted_capacity[c], demand_state[c]
        vc = demand / cap if cap > 0 else float("inf")
        rows.append(
            {
                "corridor": c,
                "demand": round(demand, 1),
                "capacity": round(cap, 1),
                "vc_ratio": round(vc, 3) if cap > 0 else float("inf"),
                "color": get_color(vc) if cap > 0 else "red",
            }
        )
    state_df = pd.DataFrame(rows).sort_values("vc_ratio", ascending=False)

    yield {
        "type": "result",
        "stage": "inject_disaster",
        "state": state_df,
        "spillover_received": spillover_received,
        "unresolved": unresolved,
    }


def inject_disaster(target_corridors, hour, capacity_remaining_pct=0.0, max_iterations=10, protect=None):
    """Same computation as inject_disaster_stream, collected into the
    single return value the existing /simulate, /route, and /playbook
    endpoints expect. Kept so nothing downstream has to change."""
    result = None
    for event in inject_disaster_stream(target_corridors, hour, capacity_remaining_pct, max_iterations, protect):
        if event["type"] == "result":
            result = event
    return result["state"], result["spillover_received"], result["unresolved"]


def build_travel_time_graph(network_state_df):
    vc_lookup = network_state_df.set_index("corridor")["vc_ratio"].to_dict()
    G_time = nx.Graph()
    G_time.add_nodes_from(data.G_sim.nodes())
    for u, v, d in data.G_sim.edges(data=True):
        dist = d["weight"]
        edge_vc = max(vc_lookup.get(u, 0), vc_lookup.get(v, 0))
        G_time.add_edge(u, v, weight=bpr_travel_time_min(dist, edge_vc), distance_km=dist, vc_used=edge_vc)
    return G_time


def stress_test_plan_stream(target_corridors, hour, capacity_remaining_pct=0.0, protect=None, protect_threshold=None):
    """Generator version of stress_test_plan -- forwards every event from
    the underlying inject_disaster_stream call(s), plus its own 'log'
    events for the protected-route check and reroute decision, then a
    final 'result' event carrying the same (state_df, result_dict) data
    stress_test_plan returns."""
    protect = protect if protect is not None else data.protected_routes
    protect_threshold = protect_threshold if protect_threshold is not None else data.protected_vc_threshold

    yield {
        "type": "log",
        "stage": "stress_test",
        "message": f"Running initial disaster injection, checking against protected routes: {', '.join(protect)}.",
    }

    state = None
    for event in inject_disaster_stream(target_corridors, hour, capacity_remaining_pct):
        if event["type"] == "result":
            state = event["state"]
        else:
            yield event

    vc_lookup = state.set_index("corridor")["vc_ratio"].to_dict()
    violated = [c for c in protect if vc_lookup.get(c, 0) > protect_threshold]

    if not violated:
        yield {
            "type": "log",
            "stage": "stress_test",
            "message": "All protected routes remain within threshold. Stress test PASSED.",
        }
        yield {
            "type": "result",
            "stage": "stress_test",
            "state": state,
            "result": {"status": "PASSED", "resolved_by_reroute": False, "violated_initially": []},
        }
        return

    yield {
        "type": "log",
        "stage": "stress_test",
        "message": f"Protected route violation detected on {', '.join(violated)}. "
                   f"Re-running with those routes excluded as spillover recipients.",
    }

    state2 = None
    for event in inject_disaster_stream(target_corridors, hour, capacity_remaining_pct, protect=violated):
        if event["type"] == "result":
            state2 = event["state"]
        else:
            yield event

    vc_lookup2 = state2.set_index("corridor")["vc_ratio"].to_dict()
    still_violated = [c for c in protect if vc_lookup2.get(c, 0) > protect_threshold]

    status = "PASSED_AFTER_REROUTE" if not still_violated else "FAILED_PROTECTED_ROUTE"
    yield {
        "type": "log",
        "stage": "stress_test",
        "message": f"Reroute result: {status}."
                   + ("" if not still_violated else f" Still violated: {', '.join(still_violated)}."),
    }
    yield {
        "type": "result",
        "stage": "stress_test",
        "state": state2,
        "result": {
            "status": status,
            "resolved_by_reroute": True,
            "violated_initially": violated,
            "still_violated": still_violated,
        },
    }


def stress_test_plan(target_corridors, hour, capacity_remaining_pct=0.0, protect=None, protect_threshold=None):
    """Same computation as stress_test_plan_stream, collected into the
    single return value the existing /stress-test and /playbook endpoints
    expect."""
    final = None
    for event in stress_test_plan_stream(target_corridors, hour, capacity_remaining_pct, protect, protect_threshold):
        if event["type"] == "result":
            final = event
    return final["state"], final["result"]