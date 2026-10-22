import json
from pathlib import Path

import pandas as pd



BASE_DIR = Path(__file__).resolve().parent.parent


DATA_FILE = BASE_DIR / "pollution_data.json"


def load_data():

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_FILE}"
        )

    with open(DATA_FILE, "r") as f:
        data = json.load(f)


    if isinstance(data, dict) and "data" in data:
        df = pd.DataFrame(data["data"])
    else:
        df = pd.DataFrame(data)

    return df


def clean_data(df):

    numeric_columns = [
        "PM2.5",
        "PM10",
        "NO2",
        "SO2",
        "CO",
        "O3",
        "AQI",
        "Water_pollution",
        "Land_pollution"
    ]

    
    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    
    if "date" in df.columns:

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

    
    df = df.drop_duplicates()

    
    if "date" in df.columns:

        df = df.dropna(
            subset=["date"]
        )

    return df