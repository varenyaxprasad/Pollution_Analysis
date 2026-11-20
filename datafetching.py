import calendar
import json
import os
import re
from datetime import date, timedelta

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

token = os.getenv("GROQ_API_KEY")
if not token:
    raise ValueError("GROQ_API_KEY not found. Check your .env file.")

model = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=token,
    temperature=0.2,
    max_tokens=12000,
    timeout=60,
    max_retries=2,
)

AIR_METRICS = [
    "PM2.5",
    "PM10",
    "NO2",
    "SO2",
    "CO",
    "O3",
    "AQI",
]

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

METRIC_GROUPS = {
    "air": AIR_METRICS,
    "water": WATER_METRICS,
    "land": LAND_METRICS,
    "all": AIR_METRICS + WATER_METRICS + LAND_METRICS,
}

METRIC_EXAMPLES = {
    "PM2.5": 45, "PM10": 80, "NO2": 30, "SO2": 10,
    "CO": 0.5, "O3": 40, "AQI": 90,
    "Water_pH": 7.2, "Water_Dissolved_Oxygen_mg_L": 6.5,
    "Water_BOD_mg_L": 3.1, "Water_COD_mg_L": 12,
    "Water_Turbidity_NTU": 4, "Water_TDS_mg_L": 280,
    "Water_Nitrate_mg_L": 2.4, "Water_Phosphate_mg_L": 0.3,
    "Water_Lead_mg_L": 0.002, "Water_Cadmium_mg_L": 0.0004,
    "Water_Arsenic_mg_L": 0.001, "Water_Mercury_mg_L": 0.0001,
    "Land_pH": 6.8, "Land_Lead_mg_kg": 24,
    "Land_Cadmium_mg_kg": 0.4, "Land_Arsenic_mg_kg": 5,
    "Land_Mercury_mg_kg": 0.03, "Land_Chromium_mg_kg": 35,
    "Land_Nickel_mg_kg": 18, "Land_Pesticide_Residue_mg_kg": 0.2,
    "Land_Nitrate_mg_kg": 12, "Land_Phosphate_mg_kg": 8,
    "Land_Petroleum_Hydrocarbons_mg_kg": 15,
}


def build_prompt(place, dates, pollution_type, metrics):
    example = {"date": dates[0], "location": place}
    example.update({metric: METRIC_EXAMPLES[metric] for metric in metrics})
    return f"""
Generate synthetic daily {pollution_type} pollution data for a visualization project.
Location: {place}
Create exactly one record for each date, in this order:
{chr(10).join(dates)}

Return one valid JSON object with a data array. Each record must follow this
example structure (use the correct date for each record):
{json.dumps(example, ensure_ascii=False)}

Rules:
- Include every supplied date exactly once, in the same order.
- Use the exact date strings supplied and location "{place}" in every record.
- Include ONLY these measurements: {", ".join(metrics)}.
- Every measurement must be a JSON number, not a string.
- Keep values non-negative, except pH values, which must be between 0 and 14.
- These are synthetic examples, not real measurements.
- Return JSON only, without markdown or explanation.
"""


def add_months(start_date, months):
    """Return the same day in a later month, clamped to that month's last day."""
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def create_batches(start_date, end_date, batch_size=5):
    """Split the date range into small requests to help keep model responses complete."""
    batches = []
    current_date = start_date

    while current_date <= end_date:
        batch = []

        for _ in range(batch_size):
            if current_date > end_date:
                break

            batch.append(current_date.isoformat())
            current_date += timedelta(days=1)

        if batch:
            batches.append(batch)

    return batches


def extract_json(text):
    """Extract and parse a JSON object or array from a model response."""
    text = text.strip()
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

    start_obj = text.find("{")
    start_arr = text.find("[")
    starts = [position for position in (start_obj, start_arr) if position >= 0]

    if not starts:
        raise ValueError("No JSON object or array found in model response.")

    start = min(starts)
    closing = "}" if text[start] == "{" else "]"
    end = text.rfind(closing)

    if end < start:
        raise ValueError("JSON appears incomplete or truncated.")

    return json.loads(text[start : end + 1])


def normalise_records(parsed, place, batch_dates, metrics):
    """Validate output and keep only the requested group's numeric fields."""
    if isinstance(parsed, dict):
        generated = parsed.get("data", [])
    elif isinstance(parsed, list):
        generated = parsed
    else:
        generated = []

    if not isinstance(generated, list) or not generated:
        raise ValueError("The model returned no data records.")

    generated_by_date = {}

    for record in generated:
        if not isinstance(record, dict):
            continue

        record_date = str(record.get("date", ""))[:10]
        if record_date:
            generated_by_date[record_date] = record

    missing_dates = [
        requested_date
        for requested_date in batch_dates
        if requested_date not in generated_by_date
    ]

    if missing_dates:
        raise ValueError("Model missed dates: " + ", ".join(missing_dates))

    records = []

    for requested_date in batch_dates:
        source = generated_by_date[requested_date]
        record = {
            "date": requested_date,
            "location": place,
        }

        for metric in metrics:
            value = source.get(metric)

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Invalid or missing numeric value for "
                        f"{metric} on {requested_date}."
                    )

            if metric.endswith("_pH") and not 0 <= value <= 14:
                raise ValueError(
                    f"{metric} must be between 0 and 14 on {requested_date}."
                )

            if not metric.endswith("_pH") and value < 0:
                raise ValueError(
                    f"{metric} cannot be negative on {requested_date}."
                )

            record[metric] = value

        records.append(record)

    return records


def generate_batch(place, batch_dates, pollution_type, metrics):
    """Generate a batch and split it if the model response is invalid."""
    last_error = None

    for _ in range(2):
        try:
            prompt = build_prompt(place, batch_dates, pollution_type, metrics)
            response = model.invoke(prompt)

            raw_text = response.content

            if isinstance(raw_text, list):
                raw_text = "".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in raw_text
                )

            if not raw_text or not str(raw_text).strip():
                raise ValueError("The model returned an empty response.")

            parsed = extract_json(str(raw_text))
            return normalise_records(parsed, place, batch_dates, metrics)

        except Exception as exc:
            last_error = exc

    if len(batch_dates) > 1:
        midpoint = len(batch_dates) // 2
        left = generate_batch(
            place, batch_dates[:midpoint], pollution_type, metrics
        )
        right = generate_batch(
            place, batch_dates[midpoint:], pollution_type, metrics
        )
        return left + right

    raise RuntimeError(
        f"Could not generate valid data for {batch_dates[0]}. "
        f"Last error: {last_error}"
    ) from last_error


def generate_pollution_data(
    place, months, pollution_type="all", progress_callback=None
):
    """Generate synthetic data for air, water, land, or all groups."""
    if not isinstance(months, int) or not 1 <= months <= 12:
        raise ValueError("months must be an integer from 1 to 12.")

    place = str(place).strip()
    if not place:
        raise ValueError("Please provide a location.")

    pollution_type = str(pollution_type).strip().lower()
    if pollution_type not in METRIC_GROUPS:
        raise ValueError("pollution_type must be air, water, land, or all.")
    metrics = METRIC_GROUPS[pollution_type]

    # Generate a trailing period ending today, so recent dashboard filters match.
    requested_end_date = date.today()
    start_date = add_months(requested_end_date, -months)

    batches = create_batches(start_date, requested_end_date, batch_size=5)
    all_records = []
    total_batches = len(batches)

    for index, batch_dates in enumerate(batches):
        all_records.extend(
            generate_batch(place, batch_dates, pollution_type, metrics)
        )

        if progress_callback:
            progress_callback((index + 1) / total_batches)

    expected_count = (requested_end_date - start_date).days + 1

    if len(all_records) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} daily records but generated "
            f"{len(all_records)}."
        )

    return {"data": all_records}


def save_pollution_data(result):
    """Save pollution_data.json in the project root, one level above src/."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "pollution_data.json")

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)

    return file_path
