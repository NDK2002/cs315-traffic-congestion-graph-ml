"""Download hourly Hàng Xanh weather from Open-Meteo Historical Weather API."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent
API_URL = "https://archive-api.open-meteo.com/v1/archive"
LATITUDE = 10.8012
LONGITUDE = 106.7114
TIMEZONE = "Asia/Ho_Chi_Minh"
VARIABLES = ("temperature_2m", "relative_humidity_2m", "precipitation")


def fetch_weather(start_date: str, end_date: str) -> pd.DataFrame:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(VARIABLES),
        "timezone": TIMEZONE,
    }
    response = requests.get(API_URL, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload.get("reason", "Open-Meteo returned an error"))

    hourly = payload.get("hourly", {})
    missing = {"time", *VARIABLES}.difference(hourly)
    if missing:
        raise RuntimeError(f"Open-Meteo response is missing fields: {sorted(missing)}")

    frame = pd.DataFrame({key: hourly[key] for key in ("time", *VARIABLES)})
    frame["time"] = pd.to_datetime(frame["time"], errors="raise")
    frame = frame.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    if frame[list(VARIABLES)].isna().any().any():
        raise RuntimeError("Open-Meteo returned missing weather values")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default="2026-11-05")
    parser.add_argument("--end-date", default="2026-11-07")
    parser.add_argument("--output", type=Path, default=ROOT / "open_meteo_sample.csv")
    args = parser.parse_args()

    frame = fetch_weather(args.start_date, args.end_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame["time"] = frame["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    frame.to_csv(args.output, index=False, float_format="%.3f", encoding="utf-8")
    print(f"Saved {len(frame)} hourly records to {args.output}")
    print(f"Range: {frame['time'].iloc[0]} to {frame['time'].iloc[-1]} ({TIMEZONE})")


if __name__ == "__main__":
    main()
