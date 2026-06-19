"""
Signal override recommendation -- deterministic, not LLM-driven. For any
corridor at or above the red threshold, recommends extending the green
phase proportionally to how far over threshold it is. There is no live
signal hardware integration anywhere in this system -- this is intentionally
a simple, explainable rule, consistent with the "Honest AI" framing: a
deterministic formula, not a model guessing at signal timing.
"""
RED_THRESHOLD = 0.9
BASE_EXTENSION_SECONDS = 10
MAX_EXTENSION_SECONDS = 30


def generate_signal_overrides(network_state_records):
    overrides = []
    for row in network_state_records:
        vc = row.get("vc_ratio")
        if vc is None or vc < RED_THRESHOLD:
            continue
        overage = min(vc - RED_THRESHOLD, 1.0)
        extension = round(BASE_EXTENSION_SECONDS + overage * (MAX_EXTENSION_SECONDS - BASE_EXTENSION_SECONDS))
        overrides.append({
            "corridor": row["corridor"],
            "vc_ratio": vc,
            "green_phase_extension_seconds": extension,
            "instruction": f"Extend green phase on {row['corridor']} approaches by {extension}s.",
        })
    return {"signal_overrides": overrides}