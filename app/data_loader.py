"""
Loads everything exported from the Colab notebook once, at process startup,
and rebuilds the in-memory objects (graph, dataframes, model) the rest of
the app needs. One shared `data` instance is imported everywhere else.
"""
import json
import os

import networkx as nx
import pandas as pd
import xgboost as xgb

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class BlockBusterData:
    def __init__(self):
        with open(os.path.join(DATA_DIR, "blockbuster_export_final.json")) as f:
            export = json.load(f)

        self.corridors = export["corridors"]
        self.corridor_centroids = pd.DataFrame(export["corridor_centroids"])
        self.capacity = {k: float(v) for k, v in export["capacity"].items()}
        self.demand_share_compressed = {
            k: float(v) for k, v in export["demand_share_compressed"].items()
        }
        self.diurnal_factor = {int(k): float(v) for k, v in export["diurnal_factor"].items()}
        self.peak_demand_scale = float(export["peak_demand_scale"])
        self.station_locations = pd.DataFrame(export["station_locations"])
        self.junction_candidates = pd.DataFrame(export["junction_candidates"])
        self.model_feature_cols = export["model_feature_cols"]
        self.bpr_params = export["bpr_params"]
        self.protected_routes = export["protected_routes"]
        self.protected_vc_threshold = float(export["protected_vc_threshold"])
        self.officer_roster = pd.DataFrame(export["officer_roster"])

        # Rebuild the corridor graph (same topology as G_sim in the notebook)
        self.G_sim = nx.Graph()
        self.G_sim.add_nodes_from(self.corridors)
        for edge in export["graph_edges"]:
            self.G_sim.add_edge(edge["source"], edge["target"], weight=edge["distance_km"])

        # Historical panel, needed to compute live past_7d/past_30d features
        panel_df = pd.read_json(os.path.join(DATA_DIR, "blockbuster_panel.json"))
        panel_df["bin_start"] = pd.to_datetime(panel_df["bin_start"], utc=True)
        self.panel = panel_df

        # Trained model, loaded via XGBoost's native portable format
        self.model = xgb.XGBClassifier()
        self.model.load_model(os.path.join(DATA_DIR, "blockbuster_model.json"))


# Loaded once when the app starts; every module imports this same instance
data = BlockBusterData()
