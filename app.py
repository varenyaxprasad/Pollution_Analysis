import base64
import html
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from datafetching import generate_pollution_data, save_pollution_data
except Exception as exc:
    generate_pollution_data = None
    save_pollution_data = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = None


st.set_page_config(
    page_title="Pollution Analytics",
    page_icon="🌍",
    layout="wide",
)

AIR_METRICS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]

WATER_METRICS = [
    "Water_pH",
    "Water_Dissolved_Oxygen_mg_L",
    "Water_BOD_mg_L",
    "Water_COD_mg_L",
    "Water_Turbidity_NTU",
    "Water_TDS_mg_L",
    "Water_Nitrate_mg_L",
    "Water_Phosphate_mg_L",
    "Water_Lead_mg_L",
    "Water_Cadmium_mg_L",
    "Water_Arsenic_mg_L",
    "Water_Mercury_mg_L",
]

LAND_METRICS = [
    "Land_pH",
    "Land_Lead_mg_kg",
    "Land_Cadmium_mg_kg",
    "Land_Arsenic_mg_kg",
    "Land_Mercury_mg_kg",
    "Land_Chromium_mg_kg",
    "Land_Nickel_mg_kg",
    "Land_Pesticide_Residue_mg_kg",
    "Land_Nitrate_mg_kg",
    "Land_Phosphate_mg_kg",
    "Land_Petroleum_Hydrocarbons_mg_kg",
]

ALL_METRICS = AIR_METRICS + WATER_METRICS + LAND_METRICS

CORRELATION_GROUPS = {
    "Air": AIR_METRICS,
    "Water": WATER_METRICS,
    "Land / soil": LAND_METRICS,
}

METRIC_LABELS = {
    "Water_pH": "Water pH",
    "Water_Dissolved_Oxygen_mg_L": "Dissolved oxygen (mg/L)",
    "Water_BOD_mg_L": "Biochemical oxygen demand (mg/L)",
    "Water_COD_mg_L": "Chemical oxygen demand (mg/L)",
    "Water_Turbidity_NTU": "Turbidity (NTU)",
    "Water_TDS_mg_L": "Total dissolved solids (mg/L)",
    "Water_Nitrate_mg_L": "Nitrate (mg/L)",
    "Water_Phosphate_mg_L": "Phosphate (mg/L)",
    "Water_Lead_mg_L": "Lead (mg/L)",
    "Water_Cadmium_mg_L": "Cadmium (mg/L)",
    "Water_Arsenic_mg_L": "Arsenic (mg/L)",
    "Water_Mercury_mg_L": "Mercury (mg/L)",
    "Land_pH": "Soil pH",
    "Land_Lead_mg_kg": "Lead (mg/kg)",
    "Land_Cadmium_mg_kg": "Cadmium (mg/kg)",
    "Land_Arsenic_mg_kg": "Arsenic (mg/kg)",
    "Land_Mercury_mg_kg": "Mercury (mg/kg)",
    "Land_Chromium_mg_kg": "Chromium (mg/kg)",
    "Land_Nickel_mg_kg": "Nickel (mg/kg)",
    "Land_Pesticide_Residue_mg_kg": "Pesticide residue (mg/kg)",
    "Land_Nitrate_mg_kg": "Nitrate (mg/kg)",
    "Land_Phosphate_mg_kg": "Phosphate (mg/kg)",
    "Land_Petroleum_Hydrocarbons_mg_kg": "Petroleum hydrocarbons (mg/kg)",
}


def metric_label(metric):
    return METRIC_LABELS.get(metric, metric.replace("_", " "))


def find_wallpapers():
    """Use only the pollution photo supplied for the dashboard wallpaper."""
    project_root = Path(__file__).resolve().parent.parent
    wallpaper = project_root / "assets" / "wallpapers" / "photo-environment-pollution_731790-164062.webp"
    return [wallpaper] if wallpaper.is_file() else []


def add_wallpaper():
    """Show the supplied pollution photo as one softly blurred background."""
    images = find_wallpapers()
    if not images:
        return

    try:
        raw_image = images[0].read_bytes()
    except OSError:
        return

    encoded_image = base64.b64encode(raw_image).decode("ascii")
    wallpaper_html = f"""
    <style>
        .stApp {{
            background-color: #080b10 !important;
            color: #e8edf2 !important;
        }}
        [data-testid="stMainBlockContainer"] {{
            max-width: 1700px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }}
        h1, h2, h3 {{
            letter-spacing: -0.035em;
        }}
        h1 {{
            font-size: clamp(2rem, 3vw, 3rem) !important;
            margin-bottom: 0.25rem !important;
        }}
        [data-testid="stMetric"] {{
            background: linear-gradient(145deg, rgba(25, 29, 36, .94), rgba(13, 17, 23, .96));
            border: 1px solid rgba(255, 154, 77, .18);
            border-radius: 12px;
            padding: 14px 16px;
            min-height: 104px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
        }}
        [data-testid="stMetricLabel"] {{
            color: #9ca6b1 !important;
            font-size: .78rem !important;
            text-transform: uppercase;
            letter-spacing: .08em;
        }}
        [data-testid="stMetricValue"] {{
            color: #f5f7f9 !important;
            font-size: 1.8rem !important;
        }}
        [data-testid="stTabs"] button {{
            color: #a8b0ba;
            font-size: .9rem;
        }}
        [data-testid="stTabs"] button[aria-selected="true"] {{
            color: #ffad67 !important;
            border-bottom-color: #ff914d !important;
        }}
        [data-testid="stSidebar"] h2 {{
            color: #f3f5f7;
            letter-spacing: .02em;
        }}
        [data-testid="stSidebar"] label {{
            color: #c3cbd3 !important;
        }}
        [data-testid="stButton"] button[kind="primary"] {{
            background: linear-gradient(100deg, #ff754d, #ff9c4a) !important;
            border: 1px solid rgba(255, 190, 125, .55) !important;
            color: #fff !important;
            font-weight: 700 !important;
            box-shadow: 0 6px 20px rgba(255, 117, 77, .2);
        }}
        [data-testid="stButton"] button[kind="primary"]:hover {{
            background: linear-gradient(100deg, #ff8b58, #ffb15f) !important;
            transform: translateY(-2px);
            box-shadow: 0 9px 25px rgba(255, 117, 77, .34);
        }}
        [data-testid="stPlotlyChart"] {{
            background: rgba(10, 14, 20, .88);
            border: 1px solid rgba(255, 255, 255, .08);
            border-radius: 13px;
            padding: 5px;
            box-shadow: 0 10px 30px rgba(0,0,0,.16);
        }}
        .monitor-heading {{
            border-left: 3px solid #ff914d;
            padding: 2px 0 4px 16px;
            margin: 5px 0 20px;
        }}
        .monitor-heading .eyebrow {{
            color: #ffad67;
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .16em;
            text-transform: uppercase;
        }}
        .monitor-heading p {{
            color: #9ca6b1;
            margin: 0;
        }}
        .section-kicker {{
            color: #ffad67;
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .14em;
            text-transform: uppercase;
            margin: 12px 0 2px;
        }}
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stHeader"] {{
            background: transparent !important;
        }}
        [data-testid="stMainBlockContainer"] {{
            position: relative;
            z-index: 2;
            background: transparent !important;
        }}
        [data-testid="stSidebar"] {{
            position: relative;
            z-index: 3;
            background: rgba(10, 16, 21, 0.91) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .wallpaper-stage {{
            position: fixed;
            inset: -14px;
            z-index: 0;
            overflow: hidden;
            pointer-events: none;
            background: #0b1116;
        }}
        .wallpaper-stage img {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center;
            filter: blur(4px) brightness(0.68) saturate(0.9);
            transform: scale(1.03);
        }}
        .wallpaper-shade {{
            position: absolute;
            inset: 0;
            background: rgba(5, 10, 14, 0.38);
        }}
        .dashboard-card {{
            background: linear-gradient(120deg, rgba(20, 25, 32, .96), rgba(12, 17, 23, .95));
            border: 1px solid rgba(255, 145, 77, .22);
            border-radius: 13px;
            padding: 16px 19px;
            margin: 10px 0 14px;
            backdrop-filter: blur(10px);
            transition: transform .28s ease, border-color .28s ease, box-shadow .28s ease;
        }}
        [data-testid="stMetric"],
        [data-testid="stPlotlyChart"] {{
            transition: transform .28s ease, border-color .28s ease, box-shadow .28s ease;
        }}
        [data-testid="stMetric"]:hover,
        [data-testid="stPlotlyChart"]:hover,
        .dashboard-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(255, 145, 77, .48);
            box-shadow: 0 14px 34px rgba(0, 0, 0, .3), 0 0 18px rgba(255, 145, 77, .08);
        }}
        @keyframes scrollReveal {{
            from {{ opacity: 0; transform: translateY(34px) scale(.985); filter: blur(4px); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }}
        }}
        @keyframes scrollProgress {{
            to {{ transform: scaleX(1); }}
        }}
        @supports (animation-timeline: view()) {{
            [data-testid="stPlotlyChart"],
            [data-testid="stMetric"],
            .dashboard-card {{
                animation: scrollReveal .75s ease both;
                animation-timeline: view();
                animation-range: entry 0% entry 48%;
            }}
        }}
        @supports (animation-timeline: scroll()) {{
            body::before {{
                content: "";
                position: fixed;
                z-index: 999999;
                inset: 0 auto auto 0;
                width: 100%;
                height: 3px;
                transform: scaleX(0);
                transform-origin: left center;
                background: linear-gradient(90deg, #ff744f, #ffba69, #55c6d8);
                box-shadow: 0 0 12px rgba(255, 145, 77, .65);
                animation: scrollProgress linear both;
                animation-timeline: scroll(root block);
            }}
            .wallpaper-stage img {{
                animation: wallpaperParallax linear both;
                animation-timeline: scroll(root block);
            }}
            @keyframes wallpaperParallax {{
                from {{ transform: scale(1.03) translateY(-1%); }}
                to {{ transform: scale(1.12) translateY(3%); }}
            }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                scroll-behavior: auto !important;
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
            }}
            .wallpaper-stage img {{ transform: none; }}
        }}
    </style>
    <div class="wallpaper-stage" aria-hidden="true">
        <img src="data:image/webp;base64,{encoded_image}" alt="" />
        <div class="wallpaper-shade"></div>
    </div>
    """

    if hasattr(st, "html"):
        st.html(wallpaper_html)
    else:
        st.markdown(wallpaper_html, unsafe_allow_html=True)

def style_chart(fig):
    """Make charts transparent over the wallpaper."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f4f7f9"),
        hoverlabel=dict(
            bgcolor="#14232c",
            font_color="#ffffff",
        ),
        margin=dict(l=45, r=35, t=75, b=55),
    )
    return fig


def dataset_path():
    """Find pollution_data.json in src/ or the project root."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "pollution_data.json",
        here.parent / "pollution_data.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[-1]


def load_dataset():
    """Load the saved pollution database."""
    path = dataset_path()
    if not path.exists():
        return pd.DataFrame()

    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        records = payload.get("data", []) if isinstance(payload, dict) else payload
        return pd.DataFrame(records)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return pd.DataFrame()


def clean_frame(frame):
    """Convert dates and pollution measurements to usable types."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    df = frame.copy()

    if "location" not in df.columns:
        df["location"] = "Unknown"

    df["location"] = df["location"].fillna("Unknown").astype(str).str.strip()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

    for column in ALL_METRICS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df.drop_duplicates()


def ph_summary_chart(data, metric, title, chart_key, line_color):
    """Graph daily pH and mark its average, maximum, minimum, and dates."""
    if metric not in data.columns or "date" not in data.columns:
        st.info(f"{title} data is not available.")
        return

    chart_data = (
        data[["date", metric]]
        .dropna(subset=[metric])
        .sort_values("date")
        .copy()
    )

    if chart_data.empty:
        st.info(f"No {title.lower()} values are available for this period.")
        return

    average_value = float(chart_data[metric].mean())
    max_row = chart_data.loc[chart_data[metric].idxmax()]
    min_row = chart_data.loc[chart_data[metric].idxmin()]

    max_date = pd.Timestamp(max_row["date"])
    min_date = pd.Timestamp(min_row["date"])
    max_value = float(max_row[metric])
    min_value = float(min_row[metric])

    fig = px.line(
        chart_data,
        x="date",
        y=metric,
        markers=True,
        title=title,
    )

    fig.update_traces(
        line=dict(color=line_color, width=3),
        marker=dict(size=7),
        name="Daily pH",
        hovertemplate="%{x|%d %b %Y}<br>pH: %{y:.2f}<extra></extra>",
    )

    fig.add_hline(
        y=average_value,
        line_dash="dash",
        line_color="#f0c674",
        annotation_text=f"Average: {average_value:.2f}",
        annotation_position="top left",
        annotation_font_color="#f0c674",
    )

    fig.add_trace(
        go.Scatter(
            x=[max_date],
            y=[max_value],
            mode="markers+text",
            name="Maximum",
            text=[f"Max {max_value:.2f}<br>{max_date:%d %b %Y}"],
            textposition="top center",
            marker=dict(
                color="#ff6b6b",
                size=12,
                symbol="star",
                line=dict(color="#ffffff", width=1),
            ),
            hovertemplate=(
                f"Maximum pH: {max_value:.2f}<br>"
                f"Date: {max_date:%d %b %Y}<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[min_date],
            y=[min_value],
            mode="markers+text",
            name="Minimum",
            text=[f"Min {min_value:.2f}<br>{min_date:%d %b %Y}"],
            textposition="bottom center",
            marker=dict(
                color="#66d9a8",
                size=12,
                symbol="star",
                line=dict(color="#ffffff", width=1),
            ),
            hovertemplate=(
                f"Minimum pH: {min_value:.2f}<br>"
                f"Date: {min_date:%d %b %Y}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="pH",
        legend_title="",
    )

    st.plotly_chart(
        style_chart(fig),
        use_container_width=True,
        key=chart_key,
    )


def metric_line_chart(data, metric, chart_key):
    """Create one uniquely keyed, interactive time-series chart."""
    if metric not in data.columns:
        return

    chart_data = data.dropna(subset=[metric]).sort_values("date")
    if chart_data.empty:
        return

    fig = px.line(
        chart_data,
        x="date",
        y=metric,
        markers=True,
        title=f"{metric_label(metric)} over time",
        hover_data=["location"],
    )
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=7),
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=metric_label(metric),
        showlegend=False,
    )

    st.plotly_chart(
        style_chart(fig),
        use_container_width=True,
        key=chart_key,
    )


def plot_all_metrics(data, metrics, group_key):
    """Display a separate graph for every available measurement."""
    available = [
        metric
        for metric in metrics
        if metric in data.columns and data[metric].notna().any()
    ]

    if not available:
        st.info(
            "No measurements are available. Generate this city's data again "
            "using the updated datafetching.py."
        )
        return

    for start in range(0, len(available), 2):
        columns = st.columns(2)

        for offset, column in enumerate(columns):
            index = start + offset
            if index >= len(available):
                break

            metric = available[index]
            with column:
                metric_line_chart(
                    data,
                    metric,
                    chart_key=f"{group_key}_{metric}",
                )


def plot_selectable_metrics(data, metrics, group_key):
    """Show a selected graph and optional graphs for the whole group."""
    available = [
        metric
        for metric in metrics
        if metric in data.columns and data[metric].notna().any()
    ]

    if not available:
        st.info(
            "No measurements are available. Generate this city's data again "
            "using the updated datafetching.py."
        )
        return

    selected = st.selectbox(
        "Choose a measurement",
        available,
        format_func=metric_label,
        key=f"{group_key}_picker",
    )

    metric_line_chart(
        data,
        selected,
        chart_key=f"{group_key}_selected_{selected}",
    )

    with st.expander("Show all measurements"):
        plot_all_metrics(
            data,
            available,
            group_key=f"{group_key}_all",
        )


def get_previous_period_change(data, metric, start, end):
    """Compare this date range with the preceding date range."""
    if metric not in data.columns or start is None or end is None:
        return None

    period_length = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)

    previous = data.loc[
        data["date"].dt.date.between(previous_start, previous_end),
        metric,
    ].dropna()

    current = data.loc[
        data["date"].dt.date.between(start, end),
        metric,
    ].dropna()

    if previous.empty or current.empty:
        return None

    return float(current.mean() - previous.mean())


def correlation_view(data):
    """Display a readable heatmap for a selected pollution group."""
    st.subheader("Correlation explorer")
    st.caption(
        "Choose one group and a few measurements. Correlations from generated "
        "sample data are examples, not scientific findings."
    )

    group_name = st.selectbox(
        "Pollution group",
        list(CORRELATION_GROUPS.keys()),
        key="correlation_group",
    )

    candidates = [
        metric
        for metric in CORRELATION_GROUPS[group_name]
        if metric in data.columns
    ]

    if len(candidates) < 2:
        st.info(f"There are not enough {group_name.lower()} fields to compare.")
        return

    selected = st.multiselect(
        "Measurements to compare",
        options=candidates,
        default=candidates[: min(5, len(candidates))],
        format_func=metric_label,
        key=f"correlation_metrics_{group_name}",
    )

    if len(selected) < 2:
        st.info("Select at least two measurements.")
        return

    usable = [
        metric
        for metric in selected
        if data[metric].notna().sum() >= 3
        and data[metric].nunique(dropna=True) > 1
    ]

    if len(usable) < 2:
        st.info(
            "At least two selected measurements need three or more values "
            "and some variation."
        )
        return

    correlation = data[usable].corr(method="pearson", min_periods=3)
    labels = {metric: metric_label(metric) for metric in usable}
    correlation = correlation.rename(index=labels, columns=labels)

    fig = px.imshow(
        correlation,
        text_auto=".2f",
        aspect="auto",
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu",
        title=f"{group_name} correlations",
        labels={
            "x": "Measurement",
            "y": "Measurement",
            "color": "Correlation",
        },
    )
    fig.update_xaxes(tickangle=-30, automargin=True)
    fig.update_yaxes(automargin=True)
    fig.update_layout(
        height=max(420, 75 * len(usable)),
        margin=dict(l=130, r=35, t=75, b=135),
    )

    st.plotly_chart(
        style_chart(fig),
        use_container_width=True,
        key=f"correlation_heatmap_{group_name}",
    )


add_wallpaper()


if "pollution_data" not in st.session_state:
    st.session_state.pollution_data = load_dataset()


with st.sidebar:
    st.header("Data controls")

    city_to_generate = st.text_input(
        "Add / generate city",
        value="Bengaluru",
        key="city_to_generate",
    ).strip()

    months_to_generate = st.slider(
        "Months to generate",
        min_value=1,
        max_value=12,
        value=6,
    )

    generation_type_label = st.selectbox(
        "Pollution data to generate",
        ["Air only", "Water only", "Land & soil only", "All pollution types"],
        index=0,
        help="Generate only the selected pollution group to reduce API usage.",
    )
    generation_type = {
        "Air only": "air",
        "Water only": "water",
        "Land & soil only": "land",
        "All pollution types": "all",
    }[generation_type_label]

    generate = st.button(
        "🚀 Generate / Add City",
        type="primary",
        use_container_width=True,
    )


if generate:
    if not city_to_generate:
        st.sidebar.error("Enter a city name first.")

    elif generate_pollution_data is None:
        st.error(
            "Could not import datafetching.py. Check that it is in the same "
            "src folder as app.py. Details: "
            + str(IMPORT_ERROR)
        )

    else:
        progress = st.progress(0)
        status = st.empty()

        try:
            result = generate_pollution_data(
                city_to_generate,
                months_to_generate,
                pollution_type=generation_type,
                progress_callback=lambda value: progress.progress(
                    max(0.0, min(1.0, float(value)))
                ),
            )

            new_df = pd.DataFrame(result.get("data", []))
            old_df = st.session_state.pollution_data

            # Combine by city/date while keeping prior pollutant groups. The
            # selected group's new values update its columns; other groups stay.
            combined = pd.concat([old_df, new_df], ignore_index=True, sort=False)
            if "date" in combined.columns and "location" in combined.columns:
                combined["date"] = pd.to_datetime(
                    combined["date"], errors="coerce"
                )
                combined = (
                    combined.dropna(subset=["date"])
                    .groupby(["date", "location"], as_index=False, sort=False)
                    .last()
                )
                combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

            st.session_state.pollution_data = combined
            st.session_state.selected_city = city_to_generate

            if save_pollution_data is not None:
                save_pollution_data(
                    {"data": combined.to_dict(orient="records")}
                )

            status.success(
                f"Added {len(new_df):,} records for {city_to_generate}."
            )
            st.rerun()

        except Exception as exc:
            status.error(f"Dataset generation failed: {exc}")


df = clean_frame(st.session_state.pollution_data)

if df.empty:
    st.info(
        "No saved dataset was found. Use the sidebar to generate data, "
        "or place pollution_data.json in the project root."
    )
    st.stop()


cities = sorted(
    city
    for city in df["location"].dropna().unique().tolist()
    if str(city).strip()
)

if not cities:
    st.warning("No city names were found in the dataset.")
    st.stop()


with st.sidebar:
    if (
        "selected_city" not in st.session_state
        or st.session_state.selected_city not in cities
    ):
        st.session_state.selected_city = cities[0]

    selected_city = st.selectbox(
        "City filter",
        options=cities,
        key="selected_city",
    )

    if "date" in df.columns and df["date"].notna().any():
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()

        picked_dates = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        picked_dates = None

    available_air_metrics = [
        metric
        for metric in AIR_METRICS[:-1]
        if metric in df.columns
    ]

    selected_air_metrics = st.multiselect(
        "Air pollutants to compare",
        available_air_metrics,
        default=available_air_metrics[:4],
    )


st.markdown(
    f"""
    <div class="monitor-heading">
      <div class="eyebrow">Pollution intelligence · monitoring console</div>
      <h1>{html.escape(selected_city)} Environmental Monitor</h1>
      <p>Interactive air, water and soil monitoring · generated sample data</p>
    </div>
    """,
    unsafe_allow_html=True,
)


filtered = df[df["location"] == selected_city].copy()
start_date = None
end_date = None

if picked_dates and "date" in filtered.columns:
    if isinstance(picked_dates, (tuple, list)) and len(picked_dates) == 2:
        start_date, end_date = picked_dates
    elif isinstance(picked_dates, date):
        start_date = end_date = picked_dates

    if start_date and end_date:
        filtered = filtered[
            filtered["date"].dt.date.between(start_date, end_date)
        ]

if filtered.empty:
    st.warning(
        "No rows match the selected city and date range. "
        "Choose a wider date range or generate data for that city."
    )
    st.stop()


aqi_data = (
    filtered.dropna(subset=["AQI"]).copy()
    if "AQI" in filtered.columns
    else pd.DataFrame()
)

if not aqi_data.empty:
    average_aqi = float(aqi_data["AQI"].mean())
    max_aqi_row = aqi_data.loc[aqi_data["AQI"].idxmax()]
    min_aqi_row = aqi_data.loc[aqi_data["AQI"].idxmin()]

    maximum_aqi = float(max_aqi_row["AQI"])
    minimum_aqi = float(min_aqi_row["AQI"])

    maximum_aqi_date = (
        max_aqi_row["date"].strftime("%d %b %Y")
        if "date" in max_aqi_row.index and pd.notna(max_aqi_row["date"])
        else "Date unavailable"
    )
    minimum_aqi_date = (
        min_aqi_row["date"].strftime("%d %b %Y")
        if "date" in min_aqi_row.index and pd.notna(min_aqi_row["date"])
        else "Date unavailable"
    )
else:
    average_aqi = maximum_aqi = minimum_aqi = float("nan")
    maximum_aqi_date = minimum_aqi_date = "Date unavailable"

aqi_change = get_previous_period_change(
    df[df["location"] == selected_city],
    "AQI",
    start_date,
    end_date,
)


k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Average AQI",
    f"{average_aqi:.1f}" if pd.notna(average_aqi) else "N/A",
    delta=(
        f"{aqi_change:+.1f} vs previous period"
        if aqi_change is not None
        else None
    ),
)
k2.metric(
    "Maximum AQI",
    f"{maximum_aqi:.1f}" if pd.notna(maximum_aqi) else "N/A",
)
k3.metric(
    "Minimum AQI",
    f"{minimum_aqi:.1f}" if pd.notna(minimum_aqi) else "N/A",
)
k4.metric("Records", f"{len(filtered):,}")


overview_tab, air_tab, water_tab, land_tab, correlation_tab, data_tab = st.tabs(
    [
        "✨ Overview",
        "🌫️ Air",
        "💧 Water",
        "🌱 Land & soil",
        "🔗 Correlations",
        "📋 Data",
    ]
)


with overview_tab:
    st.markdown('<div class="section-kicker">Air quality · selected period</div>', unsafe_allow_html=True)
    summary_columns = st.columns([1, 1, 1, 1.4])
    summary_columns[0].metric("Peak AQI date", maximum_aqi_date)
    summary_columns[1].metric("Cleanest AQI date", minimum_aqi_date)
    summary_columns[2].metric(
        "Change vs prior period",
        f"{aqi_change:+.1f}" if aqi_change is not None else "—",
        help="Difference in average AQI compared with the previous equal-length period.",
    )
    summary_columns[3].metric("Selected location", selected_city)

    gauge_column, trend_column = st.columns([1, 2.4], gap="large")
    with gauge_column:
        if pd.notna(average_aqi):
            gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=average_aqi,
                    number={"suffix": " AQI", "valueformat": ".1f"},
                    title={"text": "PERIOD AVERAGE"},
                    gauge={
                        "axis": {"range": [0, 300], "tickcolor": "#aeb7c0"},
                        "bar": {"color": "#ff914d", "thickness": 0.24},
                        "bgcolor": "rgba(0,0,0,0)",
                        "borderwidth": 0,
                        "steps": [
                            {"range": [0, 50], "color": "#244b3d"},
                            {"range": [50, 100], "color": "#665729"},
                            {"range": [100, 200], "color": "#663d2b"},
                            {"range": [200, 300], "color": "#582e34"},
                        ],
                    },
                )
            )
            gauge.update_layout(height=310, margin=dict(l=24, r=24, t=65, b=20))
            st.plotly_chart(
                style_chart(gauge),
                use_container_width=True,
                key="overview_aqi_gauge",
            )
        else:
            st.info("AQI values are missing from this selection.")

    with trend_column:
        if not aqi_data.empty and "date" in aqi_data.columns:
            ordered_aqi = aqi_data.sort_values("date")
            fig = px.area(
                ordered_aqi,
                x="date",
                y="AQI",
                markers=True,
                title="AQI trend · daily readings",
            )
            fig.update_traces(
                line=dict(color="#ff9b55", width=3),
                fillcolor="rgba(255, 145, 77, 0.15)",
                hovertemplate="%{x|%d %b %Y}<br>AQI %{y:.1f}<extra></extra>",
            )
            if pd.notna(maximum_aqi):
                max_row = aqi_data.loc[aqi_data["AQI"].idxmax()]
                fig.add_trace(go.Scatter(
                    x=[max_row["date"]], y=[maximum_aqi], mode="markers+text",
                    name="Period high", text=[f"HIGH {maximum_aqi:.0f}"],
                    textposition="top center", marker={"color": "#ff655d", "size": 11},
                    hovertemplate=f"Maximum AQI {maximum_aqi:.1f}<br>{maximum_aqi_date}<extra></extra>",
                ))
            fig.update_layout(
                xaxis_title="", yaxis_title="AQI", height=310,
                showlegend=False, margin=dict(l=35, r=25, t=55, b=35),
            )
            st.plotly_chart(
                style_chart(fig),
                use_container_width=True,
                key="overview_aqi_area",
            )
        else:
            st.info("AQI or date values are missing from the data.")

    st.markdown('<div class="section-kicker">Pollutant activity · air profile</div>', unsafe_allow_html=True)
    profile_column, heatmap_column = st.columns(2, gap="large")
    compare_metrics = [
        metric for metric in selected_air_metrics
        if metric in filtered.columns and filtered[metric].notna().any()
    ]

    with profile_column:
        if compare_metrics:
            averages = (
                filtered[compare_metrics].mean(numeric_only=True)
                .rename_axis("Pollutant").reset_index(name="Average")
            )
            averages["Pollutant"] = averages["Pollutant"].map(metric_label)
            fig = px.bar(
                averages.sort_values("Average"),
                x="Average", y="Pollutant", orientation="h",
                color="Average", color_continuous_scale=["#67412c", "#ff914d"],
                title="Average selected pollutant levels",
            )
            fig.update_layout(
                coloraxis_showscale=False, height=340,
                yaxis={"categoryorder": "total ascending"},
                xaxis_title="Average reading", margin=dict(l=25, r=20, t=55, b=35),
            )
            st.plotly_chart(
                style_chart(fig), use_container_width=True,
                key="overview_air_average_bar",
            )
        else:
            st.info("Choose air pollutants in the sidebar to compare them.")

    with heatmap_column:
        if compare_metrics and "date" in filtered.columns:
            daily = filtered.groupby(filtered["date"].dt.date)[compare_metrics].mean()
            zscores = daily.copy()
            for metric in compare_metrics:
                deviation = daily[metric].std()
                zscores[metric] = (
                    (daily[metric] - daily[metric].mean()) / deviation
                    if pd.notna(deviation) and deviation > 0
                    else 0
                )
            fig = px.imshow(
                zscores.T,
                x=[day.strftime("%d %b") for day in zscores.index],
                y=[metric_label(metric) for metric in compare_metrics],
                aspect="auto", color_continuous_scale="Oranges",
                zmin=-2, zmax=2,
                title="Daily pollutant pattern · relative to period average",
                labels={"x": "Date", "y": "Pollutant", "color": "Deviation"},
            )
            fig.update_layout(height=340, margin=dict(l=25, r=20, t=55, b=55))
            st.plotly_chart(
                style_chart(fig), use_container_width=True,
                key="overview_air_pattern_heatmap",
            )

    st.markdown('<div class="section-kicker">Water & soil indicators</div>', unsafe_allow_html=True)
    water_column, soil_column = st.columns(2, gap="large")
    with water_column:
        ph_summary_chart(
            filtered, metric="Water_pH",
            title="Water pH · average, peak and low",
            chart_key="overview_water_ph_summary", line_color="#55c6d8",
        )
    with soil_column:
        ph_summary_chart(
            filtered, metric="Land_pH",
            title="Soil pH · average, peak and low",
            chart_key="overview_soil_ph_summary", line_color="#8bcf72",
        )


with air_tab:
    st.subheader("Air pollution — individual measurements")
    st.caption(
        "Each available air pollutant has its own graph. Scroll down to see them all."
    )
    plot_all_metrics(
        filtered,
        AIR_METRICS,
        group_key="air_individual",
    )


with water_tab:
    st.subheader("Water pollution")
    plot_selectable_metrics(
        filtered,
        WATER_METRICS,
        group_key="water",
    )


with land_tab:
    st.subheader("Land and soil pollution")
    plot_selectable_metrics(
        filtered,
        LAND_METRICS,
        group_key="land",
    )


with correlation_tab:
    correlation_view(filtered)


with data_tab:
    st.subheader("Filtered records")

    search_text = st.text_input(
        "Search records",
        placeholder="Type a measurement name or value",
        key="record_search",
    )

    display_data = filtered.copy()

    if search_text:
        matches = display_data.astype(str).apply(
            lambda column: column.str.contains(
                search_text,
                case=False,
                na=False,
            )
        ).any(axis=1)
        display_data = display_data[matches]

    if "date" in display_data.columns:
        display_data = display_data.sort_values("date", ascending=False)

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download filtered CSV",
        display_data.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_city.lower()}_pollution_data.csv",
        mime="text/csv",
        use_container_width=True,
    )


with st.expander("About this dashboard"):
    st.write(
        "Air, water, and land/soil readings are generated sample values. "
        
    )
