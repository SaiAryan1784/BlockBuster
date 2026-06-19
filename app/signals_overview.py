"""
City-wide signal override recommendations for the current baseline
network state -- same deterministic formula as signal-override,
applied across all corridors at once instead of during one incident.
"""
from .network_status import get_baseline_network_state
from .signals import generate_signal_overrides


def get_signals_overview(hour):
    state = get_baseline_network_state(hour)
    return generate_signal_overrides(state.to_dict("records"))