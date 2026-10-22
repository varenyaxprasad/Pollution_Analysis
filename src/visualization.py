import plotly.express as px


def aqi_over_time(df):

    fig = px.line(
        df.sort_values("date"),
        x="date",
        y="AQI",
        color="location"
        if "location" in df.columns
        else None,
        markers=True,
        title="AQI Over Time"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="AQI"
    )

    return fig


def pm25_over_time(df):

    fig = px.line(
        df.sort_values("date"),
        x="date",
        y="PM2.5",
        color="location"
        if "location" in df.columns
        else None,
        markers=True,
        title="PM2.5 Over Time"
    )

    return fig


def pm10_over_time(df):

    fig = px.line(
        df.sort_values("date"),
        x="date",
        y="PM10",
        color="location"
        if "location" in df.columns
        else None,
        markers=True,
        title="PM10 Over Time"
    )

    return fig


def pollutant_comparison(df):

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

    averages = (
        df[available]
        .mean()
        .reset_index()
    )

    averages.columns = [
        "Pollutant",
        "Average"
    ]

    fig = px.bar(
        averages,
        x="Pollutant",
        y="Average",
        title="Average Pollutant Concentration",
        text_auto=".2f"
    )

    return fig


def pm25_vs_aqi(df):

    fig = px.scatter(
        df,
        x="PM2.5",
        y="AQI",
        color="location"
        if "location" in df.columns
        else None,
        size="PM10"
        if "PM10" in df.columns
        else None,
        hover_data=[
            c for c in [
                "date",
                "location",
                "PM2.5",
                "PM10",
                "AQI"
            ]
            if c in df.columns
        ],
        title="PM2.5 vs AQI"
    )

    return fig


def correlation_heatmap(df):

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

    correlation = df[available].corr()

    fig = px.imshow(
        correlation,
        text_auto=".2f",
        aspect="auto",
        title="Pollution Parameter Correlation"
    )

    return fig


def water_pollution(df):

    fig = px.line(
        df.sort_values("date"),
        x="date",
        y="Water_pollution",
        color="location"
        if "location" in df.columns
        else None,
        markers=True,
        title="Water Pollution Over Time"
    )

    return fig


def land_pollution(df):

    fig = px.line(
        df.sort_values("date"),
        x="date",
        y="Land_pollution",
        color="location"
        if "location" in df.columns
        else None,
        markers=True,
        title="Land Pollution Over Time"
    )

    return fig