import json
from datetime import date
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

st.set_page_config(page_title="Interactive Pollution Dashboard", page_icon="🌍", layout="wide")
st.title("🌍 Interactive Pollution Analytics Dashboard")
st.caption("Select a city and date range to update every KPI, chart, and insight. Dataset values may be synthetic.")

POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
METRICS = POLLUTANTS + ["AQI", "Water_pollution", "Land_pollution"]


def dataset_path():
    # Works when this app is stored in the project's src/ directory.
    here = Path(__file__).resolve().parent
    candidates = [here / "pollution_data.json", here.parent / "pollution_data.json"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def load_dataset():
    path = dataset_path()
    if not path.exists():
        return pd.DataFrame()
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        records = payload.get("data", []) if isinstance(payload, dict) else payload
        return pd.DataFrame(records)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return pd.DataFrame()


def clean_frame(frame):
    if frame is None or frame.empty:
        return pd.DataFrame()
    df = frame.copy()
    if "location" not in df.columns:
        df["location"] = "Unknown"
    df["location"] = df["location"].fillna("Unknown").astype(str).str.strip()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in METRICS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "date" in df.columns:
        df = df.dropna(subset=["date"])
    df = df.drop_duplicates()
    return df


if "pollution_data" not in st.session_state:
    st.session_state.pollution_data = load_dataset()

with st.sidebar:
    st.header("Data controls")
    city_to_generate = st.text_input("Add / generate city", value="Bengaluru").strip()
    months_to_generate = st.slider("Months to generate", 1, 12, 6)
    generate = st.button("🚀 Generate / Add City", type="primary", use_container_width=True)

if generate:
    if not city_to_generate:
        st.sidebar.error("Enter a city name first.")
    elif generate_pollution_data is None:
        st.error("Could not import datafetching.py. Make sure app.py and datafetching.py are in the same src folder. Details: " + str(IMPORT_ERROR))
    else:
        progress = st.progress(0)
        status = st.empty()
        try:
            result = generate_pollution_data(
                city_to_generate,
                months_to_generate,
                progress_callback=lambda value: progress.progress(max(0.0, min(1.0, float(value)))),
            )
            new_df = pd.DataFrame(result.get("data", []))
            old_df = st.session_state.pollution_data
            if not old_df.empty and "location" in old_df.columns:
                old_df = old_df[old_df["location"].astype(str).str.casefold() != city_to_generate.casefold()]
                combined = pd.concat([old_df, new_df], ignore_index=True)
            else:
                combined = new_df
            if "date" in combined.columns and "location" in combined.columns:
                combined = combined.drop_duplicates(subset=["date", "location"], keep="last")
            st.session_state.pollution_data = combined
            if save_pollution_data is not None:
                save_pollution_data({"data": combined.to_dict(orient="records")})
            status.success(f"Added {len(new_df):,} records for {city_to_generate}.")
            st.rerun()
        except Exception as exc:
            status.error(f"Dataset generation failed: {exc}")

df = clean_frame(st.session_state.pollution_data)
if df.empty:
    st.info("No saved dataset was found. Use the sidebar to generate data, or place pollution_data.json in the project root.")
    st.stop()

cities = sorted(c for c in df["location"].dropna().unique().tolist() if str(c).strip())
if not cities:
    st.warning("No city names were found in the dataset.")
    st.stop()

with st.sidebar:
    selected_cities = st.multiselect("City filter", options=cities, default=[cities[0]])
    if "date" in df.columns and df["date"].notna().any():
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        picked_dates = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    else:
        picked_dates = None
    available_pollutants = [p for p in POLLUTANTS if p in df.columns]
    selected_pollutants = st.multiselect("Pollutants to compare", available_pollutants, default=available_pollutants[:4])

if not selected_cities:
    st.warning("Choose at least one city in the sidebar.")
    st.stop()

filtered = df[df["location"].isin(selected_cities)].copy()
if picked_dates and "date" in filtered.columns:
    if isinstance(picked_dates, (tuple, list)) and len(picked_dates) == 2:
        start, end = picked_dates
    elif isinstance(picked_dates, date):
        start = end = picked_dates
    else:
        start, end = None, None
    if start and end:
        filtered = filtered[filtered["date"].dt.date.between(start, end)]

if filtered.empty:
    st.warning("No rows match the selected city/date filters. Choose a wider date range or generate data for that city.")
    st.stop()

# Dashboard header — build the city label safely without nested f-string expressions.
city_heading = " + ".join(str(city) for city in selected_cities)
st.subheader("📍 " + city_heading)
st.caption("All displayed results are recalculated from the selected cities and date range. Synthetic values are not official monitoring-station readings.")

avg_aqi = filtered["AQI"].mean() if "AQI" in filtered.columns else float("nan")
max_aqi = filtered["AQI"].max() if "AQI" in filtered.columns else float("nan")
min_aqi = filtered["AQI"].min() if "AQI" in filtered.columns else float("nan")
worst = filtered.loc[filtered["AQI"].idxmax()] if "AQI" in filtered.columns and filtered["AQI"].notna().any() else None

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Average AQI", f"{avg_aqi:.1f}" if pd.notna(avg_aqi) else "N/A")
k2.metric("Maximum AQI", f"{max_aqi:.1f}" if pd.notna(max_aqi) else "N/A")
k3.metric("Minimum AQI", f"{min_aqi:.1f}" if pd.notna(min_aqi) else "N/A")
k4.metric("Records", f"{len(filtered):,}")
k5.metric("Cities", str(filtered["location"].nunique()))

# Charts: each uses only the filtered data.
st.subheader("📈 Air quality trends")
if "AQI" in filtered.columns and "date" in filtered.columns:
    fig = px.line(filtered.sort_values("date"), x="date", y="AQI", color="location", markers=True, title="AQI over time")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("AQI or date column is missing, so the AQI trend cannot be plotted.")

c1, c2 = st.columns(2)
with c1:
    if "PM2.5" in filtered.columns and "date" in filtered.columns:
        fig = px.line(filtered.sort_values("date"), x="date", y="PM2.5", color="location", markers=True, title="PM2.5 over time")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    if "PM10" in filtered.columns and "date" in filtered.columns:
        fig = px.line(filtered.sort_values("date"), x="date", y="PM10", color="location", markers=True, title="PM10 over time")
        st.plotly_chart(fig, use_container_width=True)

if selected_pollutants:
    st.subheader("🧪 Average pollutant comparison")
    averages = filtered[selected_pollutants].mean(numeric_only=True).rename_axis("Pollutant").reset_index(name="Average")
    fig = px.bar(averages, x="Pollutant", y="Average", color="Pollutant", text_auto=".2f", title="Average values for selected pollutants")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    if "PM2.5" in filtered.columns and "AQI" in filtered.columns:
        fig = px.scatter(filtered, x="PM2.5", y="AQI", color="location", hover_data=[c for c in ["date", "location", "PM10"] if c in filtered.columns], title="PM2.5 vs AQI")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    environmental = [c for c in ["Water_pollution", "Land_pollution"] if c in filtered.columns]
    if environmental:
        long_df = filtered.melt(id_vars=[c for c in ["date", "location"] if c in filtered.columns], value_vars=environmental, var_name="Metric", value_name="Value")
        if "date" in long_df.columns:
            fig = px.line(long_df.sort_values("date"), x="date", y="Value", color="Metric", line_dash="location" if long_df["location"].nunique() > 1 else None, title="Water and land pollution over time")
        else:
            fig = px.bar(long_df, x="Metric", y="Value", color="Metric", title="Water and land pollution")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("🔗 Correlation analysis")
correlation_columns = [c for c in METRICS if c in filtered.columns and filtered[c].notna().sum() >= 2]
if len(correlation_columns) >= 2 and len(filtered) >= 2:
    corr = filtered[correlation_columns].corr(numeric_only=True)
    fig = px.imshow(corr, text_auto=".2f", aspect="auto", title="Correlation matrix")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("At least two numeric metrics with data are needed for correlation analysis.")

st.subheader("🧠 Dynamic insights")
if pd.notna(avg_aqi):
    st.markdown(f"- Average AQI for the current selection is **{avg_aqi:.1f}**.")
if worst is not None:
    worst_date = worst["date"].strftime("%d %b %Y") if "date" in worst.index and pd.notna(worst["date"]) else "an unknown date"
    st.markdown(f"- Highest recorded AQI in this filtered dataset is **{float(worst['AQI']):.1f}**, for **{worst['location']}** on **{worst_date}**.")
valid_pollutants = [p for p in POLLUTANTS if p in filtered.columns and filtered[p].notna().any()]
if valid_pollutants:
    means = filtered[valid_pollutants].mean(numeric_only=True)
    highest = means.idxmax()
    st.markdown(f"- **{highest}** has the largest raw average (**{means[highest]:.2f}**) among the selected pollutant columns. Units/scales may differ, so this is not a health-risk ranking.")
if "AQI" in filtered.columns and "date" in filtered.columns:
    daily = filtered.groupby("date", as_index=False)["AQI"].mean().dropna().sort_values("date")
    if len(daily) >= 2:
        change = float(daily["AQI"].iloc[-1] - daily["AQI"].iloc[0])
        direction = "increased" if change > 0 else "decreased" if change < 0 else "was unchanged"
        st.markdown(f"- Average AQI {direction} by **{abs(change):.1f} points** between {daily['date'].iloc[0].strftime('%d %b %Y')} and {daily['date'].iloc[-1].strftime('%d %b %Y')}.")

with st.expander("📋 View filtered records and export"):
    st.dataframe(filtered.sort_values("date", ascending=False) if "date" in filtered.columns else filtered, use_container_width=True)
    st.download_button("⬇️ Download filtered CSV", filtered.to_csv(index=False).encode("utf-8"), file_name="filtered_pollution_data.csv", mime="text/csv")

with st.expander("ℹ️ About this dashboard"):
    st.write("Changing the city or date range recalculates KPIs, charts, correlations, and insights. If data was generated by the LLM, treat it as synthetic sample data rather than verified real-world measurements.")
