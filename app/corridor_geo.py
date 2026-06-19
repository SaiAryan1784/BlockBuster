"""
Static corridor geometry for frontend map rendering -- centroids (for
placing markers) and the underlying G_sim graph edges (for drawing
connector lines between corridors). Pure passthrough of already-loaded
data; no new computation, no risk to anything existing.
"""
from .data_loader import data


def get_corridor_centroids():
    return data.corridor_centroids.to_dict("records")


def get_corridor_graph_edges():
    edges = []
    for u, v, d in data.G_sim.edges(data=True):
        edges.append({"source": u, "target": v, "distance_km": d.get("weight")})
    return edges