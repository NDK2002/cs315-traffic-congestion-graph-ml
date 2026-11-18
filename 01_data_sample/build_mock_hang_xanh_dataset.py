"""Build the documented, reproducible Hàng Xanh spatio-temporal mock dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
FEATURES_ROOT = ROOT.parent / "02_feature_selection"
START = pd.Timestamp("2026-11-05 00:00:00")
END = pd.Timestamp("2026-11-07 11:45:00")
FREQUENCY = "15min"
RANDOM_SEED = 31514
RANK = {"tertiary": 0, "secondary": 1, "primary": 2, "trunk": 3}
FREE_FLOW_BY_ROAD = {"tertiary": 31.0, "secondary": 34.0, "primary": 38.0, "trunk": 44.0}
FLOOD_SUSCEPTIBLE_ROADS = ("Đinh Bộ Lĩnh", "Xô Viết Nghệ Tĩnh", "Ung Văn Khiêm")


def _parse_maxspeed(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower().replace("km/h", "").replace("kmh", "")
    try:
        return float(text)
    except ValueError:
        return np.nan


def _static_node_features(nodes: pd.DataFrame, edges: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    edge_rows = edges.copy()
    edge_rows["maxspeed_numeric"] = edge_rows["maxspeed"].map(_parse_maxspeed)
    incoming = {int(node_id): edge_rows.loc[edge_rows["v"] == node_id] for node_id in nodes["node_id"]}
    outgoing = {int(node_id): edge_rows.loc[edge_rows["u"] == node_id] for node_id in nodes["node_id"]}
    records = []

    for node in nodes.sort_values("node_id").itertuples(index=False):
        node_id = int(node.node_id)
        in_edges = incoming[node_id]
        if in_edges.empty:
            in_edges = outgoing[node_id]
        incident_edges = edge_rows.loc[(edge_rows["u"] == node_id) | (edge_rows["v"] == node_id)]
        lane_values = pd.to_numeric(in_edges["lanes"], errors="coerce").dropna()
        speed_values = in_edges["maxspeed_numeric"].dropna()
        road_types = [part.strip() for part in str(node.highway_classes).split("|")]
        road_type = max(road_types, key=lambda value: RANK.get(value, -1))
        free_flow = FREE_FLOW_BY_ROAD.get(road_type, 34.0) + rng.normal(0, 1.0)
        road_text = str(node.roads)
        records.append({
            "node_id": node_id,
            "free_flow_kmh": round(float(free_flow), 2),
            "lanes_in_mean": float(lane_values.mean()) if not lane_values.empty else 1.0,
            "maxspeed_in_kmh": float(speed_values.mean()) if not speed_values.empty else float(free_flow),
            "in_degree": int(node.in_degree),
            "out_degree": int(node.out_degree),
            "dist_center_m": float(node.dist_center_m),
            "road_type": road_type,
            "has_twoway": int((~incident_edges["oneway"].astype(bool)).any()),
            "flood_susceptible": int(any(road in road_text for road in FLOOD_SUSCEPTIBLE_ROADS)),
        })
    return pd.DataFrame(records)


def _hourly_weather_to_quarter_hour(weather: pd.DataFrame, times: pd.DatetimeIndex) -> pd.DataFrame:
    weather = weather.copy()
    weather["time"] = pd.to_datetime(weather["time"], errors="raise")
    weather = weather.sort_values("time").drop_duplicates("time")
    weather["rain_cum_3h_mm"] = weather["precipitation"].rolling(3, min_periods=1).sum()
    return pd.merge_asof(
        pd.DataFrame({"timestamp": times}),
        weather.rename(columns={
            "time": "weather_time",
            "temperature_2m": "temperature_c",
            "relative_humidity_2m": "humidity_pct",
            "precipitation": "rain_mm_h",
        }),
        left_on="timestamp",
        right_on="weather_time",
        direction="backward",
    ).drop(columns="weather_time")


def _tide_curve(reference: pd.DataFrame, times: pd.DatetimeIndex) -> pd.Series:
    extrema = reference.copy()
    extrema["timestamp"] = pd.to_datetime(extrema["timestamp"], errors="raise")
    extrema = extrema.sort_values("timestamp").drop_duplicates("timestamp")
    points = extrema["timestamp"].astype("int64").to_numpy()
    levels = extrema["tide_level_m"].astype(float).to_numpy()
    query = times.astype("int64").to_numpy()
    if query.min() < points.min() or query.max() > points.max():
        raise ValueError("Tide extrema must bracket the full mock time range")
    right = np.searchsorted(points, query, side="right").clip(1, len(points) - 1)
    left = right - 1
    fraction = (query - points[left]) / (points[right] - points[left])
    # Cosine curve with exact values at each published high/low water extremum.
    delta = (levels[right] - levels[left]) / 2.0
    interpolated = (levels[left] + levels[right]) / 2.0 - delta * np.cos(np.pi * fraction)
    return pd.Series(interpolated, index=times, name="tide_level_m")


def _storm_mask(times: pd.DatetimeIndex) -> pd.Series:
    # Six short synthetic stress episodes: one in the initial training window and
    # one inside each of the five default validation windows.
    starts = (12, 54, 92, 130, 168, 206)
    mask = np.zeros(len(times), dtype=bool)
    for start in starts:
        mask[start:min(start + 12, len(times))] = True
    return pd.Series(mask, index=times)


def _storm_age(times: pd.DatetimeIndex) -> pd.Series:
    starts = (12, 54, 92, 130, 168, 206)
    age = np.full(len(times), -1, dtype=int)
    for start in starts:
        end = min(start + 12, len(times))
        age[start:end] = np.arange(end - start)
    return pd.Series(age, index=times)


def build_dataset(
    nodes_path: Path = ROOT / "nodes.csv",
    edges_path: Path = ROOT / "edges.csv",
    weather_path: Path = ROOT / "open_meteo_sample.csv",
    tide_path: Path = ROOT / "phu_an_tide_reference.csv",
    output_path: Path = ROOT / "mock_hang_xanh_traffic_weather.csv",
) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    nodes = pd.read_csv(nodes_path)
    edges = pd.read_csv(edges_path)
    weather = pd.read_csv(weather_path)
    tide = pd.read_csv(tide_path)
    times = pd.date_range(START, END, freq=FREQUENCY)
    static = _static_node_features(nodes, edges, rng).set_index("node_id")
    meteo = _hourly_weather_to_quarter_hour(weather, times).set_index("timestamp")
    meteo["rain_scenario_synthetic"] = _storm_mask(times).astype(int)
    meteo["_storm_age"] = _storm_age(times)
    meteo.loc[meteo["rain_scenario_synthetic"] == 1, "rain_mm_h"] = 36.0
    meteo["rain_cum_3h_mm"] = (
        meteo["rain_mm_h"].div(4).rolling(12, min_periods=1).sum()
    )
    tide_curve = _tide_curve(tide, times)
    incoming = {
        int(node_id): sorted(set(group["u"].astype(int)))
        for node_id, group in edges.groupby("v")
    }
    node_ids = sorted(static.index.astype(int))
    samples = []
    previous_ratio = {node_id: 1.0 for node_id in node_ids}

    for step, timestamp in enumerate(times):
        w = meteo.loc[timestamp]
        tide_level = float(tide_curve.loc[timestamp])
        hour = timestamp.hour + timestamp.minute / 60.0
        peak = int((6.5 <= hour < 9.0) or (16.5 <= hour < 19.0))
        time_slot = 0 if hour >= 22.0 or hour < 6.0 else (2 if peak else 1)
        is_weekend = int(timestamp.day_of_week >= 5)
        rain = float(w["rain_mm_h"])
        rain_level = (
            0 if rain < 0.1 else
            1 if rain <= 2.5 else
            2 if rain <= 10.0 else
            3 if rain <= 30.0 else 4
        )
        tide_alert = int(np.digitize(tide_level, [1.4, 1.5, 1.6], right=False))
        current_ratio = {}

        for node_id in node_ids:
            attrs = static.loc[node_id]
            predecessors = incoming.get(node_id, [])
            upstream_prev_severe = sum(previous_ratio.get(u, 1.0) < 0.3 for u in predecessors)
            road_base = {"trunk": 0.88, "primary": 0.73, "secondary": 0.68, "tertiary": 0.62}[attrs["road_type"]]
            rush_effect = 0.17 if peak and not is_weekend else (0.05 if peak else 0.0)
            rain_effect = min(rain, 12.0) * 0.006
            tide_effect = max(tide_level - 1.1, 0.0) * 0.07
            spread_effect = min(upstream_prev_severe, 2) * (0.05 if rain_level >= 3 else 0.018)
            noise = rng.normal(0, 0.035)
            ratio = road_base - rush_effect - rain_effect - tide_effect - spread_effect + noise

            # The deliberately labeled synthetic storm scenario affects susceptible
            # nodes; it is for pipeline smoke work, not observed traffic evidence.
            if bool(w["rain_scenario_synthetic"]) and attrs["flood_susceptible"]:
                if int(w["_storm_age"]) >= 4:
                    ratio = min(ratio, 0.22 + rng.uniform(0, 0.06))
                else:
                    ratio = min(ratio, 0.36 + rng.uniform(0, 0.06))
            ratio = float(np.clip(ratio, 0.12, 1.08))
            current_ratio[node_id] = ratio

        speeds = {node_id: current_ratio[node_id] * float(static.loc[node_id, "free_flow_kmh"]) for node_id in node_ids}
        for node_id in node_ids:
            attrs = static.loc[node_id]
            predecessors = incoming.get(node_id, [])
            upstream_speeds = [speeds[u] for u in predecessors if u in speeds]
            speed = float(speeds[node_id])
            speed_ratio = float(current_ratio[node_id])
            free_flow = float(attrs["free_flow_kmh"])
            class_now = 2 if speed_ratio < 0.3 else (1 if speed_ratio < 0.6 else 0)
            capacity = max(float(attrs["lanes_in_mean"]), 1.0) * 55.0
            volume = int(max(0, round(capacity * (0.35 + 0.65 * (1.0 - speed_ratio)) + rng.normal(0, 3))))
            samples.append({
                "timestamp": timestamp,
                "node_id": node_id,
                "speed_kmh": round(speed, 3),
                "volume_veh": volume,
                "speed_ratio": round(speed_ratio, 5),
                "temperature_c": float(w["temperature_c"]),
                "humidity_pct": float(w["humidity_pct"]),
                "rain_mm_h": rain,
                "rain_cum_3h_mm": float(w["rain_cum_3h_mm"]),
                "tide_level_m": tide_level,
                "hour_sin": float(np.sin(2 * np.pi * (timestamp.hour * 60 + timestamp.minute) / 1440)),
                "hour_cos": float(np.cos(2 * np.pi * (timestamp.hour * 60 + timestamp.minute) / 1440)),
                "time_slot": time_slot,
                "is_weekend": is_weekend,
                "rain_level": rain_level,
                "tide_alert": tide_alert,
                "free_flow_kmh": free_flow,
                "lanes_in_mean": float(attrs["lanes_in_mean"]),
                "maxspeed_in_kmh": float(attrs["maxspeed_in_kmh"]),
                "in_degree": int(attrs["in_degree"]),
                "out_degree": int(attrs["out_degree"]),
                "dist_center_m": float(attrs["dist_center_m"]),
                "road_type": str(attrs["road_type"]),
                "has_twoway": int(attrs["has_twoway"]),
                "upstream_speed_min": min(upstream_speeds) if upstream_speeds else free_flow,
                "upstream_congested_cnt": sum(current_ratio[u] < 0.3 for u in predecessors if u in current_ratio),
                "rain_scenario_synthetic": int(w["rain_scenario_synthetic"]),
                "_class_now": class_now,
            })
        previous_ratio = current_ratio

    frame = pd.DataFrame(samples).sort_values(["timestamp", "node_id"]).reset_index(drop=True)
    by_node = frame.groupby("node_id", sort=False)["speed_kmh"]
    for lag in (1, 2, 4):
        frame[f"speed_lag{lag}"] = by_node.shift(lag)
    frame["speed_delta1"] = frame["speed_kmh"] - frame["speed_lag1"]
    for horizon, offset in ((15, 1), (30, 2), (60, 4)):
        future = frame.groupby("node_id", sort=False)["_class_now"].shift(-offset)
        frame[f"y_t{horizon}"] = future
    frame = frame.dropna(subset=["speed_lag4", "y_t15", "y_t30", "y_t60"])
    frame[["y_t15", "y_t30", "y_t60"]] = frame[["y_t15", "y_t30", "y_t60"]].astype(int)
    frame = frame.drop(columns="_class_now")
    frame = frame.sort_values(["timestamp", "node_id"]).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, float_format="%.6f", date_format="%Y-%m-%d %H:%M:%S", encoding="utf-8")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "mock_hang_xanh_traffic_weather.csv")
    args = parser.parse_args()
    frame = build_dataset(output_path=args.output)
    print(f"Saved {len(frame):,} rows across {frame['timestamp'].nunique()} unique timestamps to {args.output}")
    for column in ("y_t15", "y_t30", "y_t60"):
        print(f"{column} class distribution: {frame[column].value_counts(normalize=True).sort_index().round(3).to_dict()}")
    print(f"Synthetic heavy-rain rows: {int(frame['rain_scenario_synthetic'].sum()):,}")


if __name__ == "__main__":
    main()
