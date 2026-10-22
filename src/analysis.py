def get_basic_statistics(df):

    stats = {

        "total_records": len(df),

        "locations": (
            df["location"].nunique()
            if "location" in df.columns
            else 0
        ),

        "average_aqi": (
            df["AQI"].mean()
            if "AQI" in df.columns
            else 0
        ),

        "maximum_aqi": (
            df["AQI"].max()
            if "AQI" in df.columns
            else 0
        ),

        "minimum_aqi": (
            df["AQI"].min()
            if "AQI" in df.columns
            else 0
        ),

        "missing_values": (
            int(df.isnull().sum().sum())
        )
    }

    return stats


def get_average_pollutants(df):

    pollutants = [
        "PM2.5",
        "PM10",
        "NO2",
        "SO2",
        "CO",
        "O3"
    ]

    available = [
        p for p in pollutants
        if p in df.columns
    ]

    return df[available].mean()


def get_correlation(df):

    columns = [
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

    available = [
        c for c in columns
        if c in df.columns
    ]

    return df[available].corr()


def get_pollution_summary(df):

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns

    return df[numeric_columns].describe().round(2)