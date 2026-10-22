import streamlit as st
import json
from datetime import date

from datafetching import (
    generate_pollution_data,
    save_pollution_data
)


st.set_page_config(
    page_title="Pollution Analytics Dashboard",
    page_icon="🌍",
    layout="wide"
)


st.title("🌍 Pollution Analytics Dashboard")

st.subheader(
    "AI-Based Pollution Data Visualization"
)

st.markdown(
    """
Synthetic pollution data generated using
**LangChain + Qwen + Hugging Face**
and analyzed using
**Python, Pandas and Plotly**.
"""
)


st.sidebar.header("Dataset Generation")


place = st.sidebar.text_input(
    "📍 Enter Location",
    value="Bengaluru"
)


months = st.sidebar.slider(
    "📅 Number of Months",
    min_value=1,
    max_value=12,
    value=6,
    step=1
)


st.sidebar.write(
    f"Selected: **{months} month(s)**"
)

st.sidebar.write(
    "Dataset starts from **1 January 2026**"
)

st.sidebar.write(
    f"Dataset ends on **{date.today().strftime('%d %B %Y')}**"
)


if "dataset" not in st.session_state:
    st.session_state.dataset = None


if st.sidebar.button(
    "🚀 Generate Dataset",
    type="primary"
):

    progress = st.progress(0)

    status = st.empty()

    try:

        status.info(
            "Generating pollution data..."
        )

        def update_progress(value):

            progress.progress(
                value
            )

            status.info(
                f"Generating data... "
                f"{int(value * 100)}%"
            )


        result = generate_pollution_data(
            place,
            months,
            progress_callback=update_progress
        )


        st.session_state.dataset = result

        save_pollution_data(
            result
        )

        progress.progress(1.0)

        status.success(
            f"Dataset generated successfully! "
            f"{len(result['data'])} records created."
        )

    except Exception as e:

        progress.empty()

        status.error(
            f"Dataset generation failed: {e}"
        )


if st.session_state.dataset is not None:

    result = st.session_state.dataset

    st.success(
        f"Dataset contains "
        f"{len(result['data'])} records."
    )

    st.subheader(
        "Generated Dataset"
    )

    st.dataframe(
        result["data"],
        use_container_width=True
    )

    json_data = json.dumps(
        result,
        indent=4
    )

    st.download_button(
        label="⬇️ Download Dataset",
        data=json_data,
        file_name="pollution_data.json",
        mime="application/json"
    )

else:

    st.info(
        "👈 Select the number of months "
        "from the sidebar and click "
        "**🚀 Generate Dataset**."
    )