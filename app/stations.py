"""Static police station locations for map rendering. Pure passthrough."""
from .data_loader import data


def get_station_locations():
    return data.station_locations.to_dict("records")