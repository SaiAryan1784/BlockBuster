"""
Baseline network status -- current diurnal traffic with no disaster
injected. A thin wrapper around the already-tested inject_disaster()
with an empty target list; no new simulation logic.
"""
from .simulation import inject_disaster


def get_baseline_network_state(hour):
    state, _, _ = inject_disaster([], hour, capacity_remaining_pct=0.0)
    return state