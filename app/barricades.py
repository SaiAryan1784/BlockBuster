"""
Barricade recommendation -- deterministic, not LLM-driven. For each
blocked corridor, recommends a barricade at its centroid (primary block).
For any corridor still at red status after redistribution, recommends a
secondary barricade to meter overflow. This is advisory output only --
same Layer 3 spirit as the rest of the engine: it never decides, it
proposes, and the Judging Panel / Watch Commander signs off.
"""
from .data_loader import data


def generate_barricade_plan(blocked_corridors, network_state_records):
    centroid_lookup = data.corridor_centroids.set_index("corridor")[["latitude", "longitude"]].to_dict("index")
    plan = []

    for corridor in blocked_corridors:
        loc = centroid_lookup.get(corridor)
        plan.append({
            "corridor": corridor,
            "reason": "primary_block",
            "latitude": loc["latitude"] if loc else None,
            "longitude": loc["longitude"] if loc else None,
            "instruction": f"Block all inflow to {corridor} at the disaster point.",
        })

    for row in network_state_records:
        if row["corridor"] in blocked_corridors:
            continue
        if row.get("color") == "red":
            loc = centroid_lookup.get(row["corridor"])
            plan.append({
                "corridor": row["corridor"],
                "reason": "overflow_management",
                "latitude": loc["latitude"] if loc else None,
                "longitude": loc["longitude"] if loc else None,
                "instruction": f"Deploy barricade to meter inflow into {row['corridor']} (V/C {row['vc_ratio']}).",
            })

    return {"barricades": plan}