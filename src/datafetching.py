import json
import os
import re
import calendar
from datetime import date, timedelta

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

load_dotenv()

token = os.getenv("GROQ_API_KEY")
if not token:
    raise ValueError("GROQ_API_KEY not found. Check your .env file.")

model = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=token,
    temperature=0.2,
    max_tokens=8000,
    timeout=60,
    max_retries=2,
)

template = PromptTemplate(
    template="""
Generate synthetic pollution data for a data-visualization project.

Location: {place}

Create exactly one record for each date in this list:
{dates}

Return a single valid JSON object in this exact structure:
{{
"data": [
    {{
    "date": "YYYY-MM-DD",
    "location": "{place}",
    "PM2.5": 45,
    "PM10": 80,
    "NO2": 30,
    "SO2": 10,
    "CO": 0.5,
    "O3": 40,
    "AQI": 90,
    "Water_pollution": 20,
    "Land_pollution": 25
    }}
]
}}

Rules:
- Include every supplied date exactly once, in the same order.
- Use the exact date strings supplied; do not invent or skip dates.
- Use "{place}" as the location for every record.
- All pollution values must be JSON numbers, not strings.
- Return JSON only. No markdown fences or explanations.
""",
    input_variables=["place", "dates"],
)

chain = template | model


def add_months(start_date, months):
    """Return the same day in a later month, clamped to that month's last day."""
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def create_batches(start_date, end_date, batch_size=10):
    """Split a date range into small requests to reduce incomplete JSON responses."""
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
    """Extract and parse a JSON object/list from a model response."""
    text = text.strip()
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

    start_obj = text.find("{")
    start_arr = text.find("[")
    starts = [pos for pos in (start_obj, start_arr) if pos >= 0]
    if not starts:
        raise ValueError("No JSON object or array found in model response.")

    start = min(starts)
    closing = "}" if text[start] == "{" else "]"
    end = text.rfind(closing)
    if end < start:
        raise ValueError("JSON appears incomplete or truncated.")

    return json.loads(text[start:end + 1])


def _normalise_records(parsed, place, batch_dates):
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

    missing_dates = [d for d in batch_dates if d not in generated_by_date]
    if missing_dates:
        raise ValueError("Model missed dates: " + ", ".join(missing_dates))

    required_metrics = [
        "PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI",
        "Water_pollution", "Land_pollution",
    ]
    records = []

    for current_date in batch_dates:
        source = generated_by_date[current_date]
        record = {"date": current_date, "location": place}
        for metric in required_metrics:
            value = source.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Invalid or missing numeric value for {metric} on {current_date}."
                    )
            record[metric] = value
        records.append(record)

    return records


def generate_batch(place, batch_dates):
    """Generate a batch; split it into smaller requests if the response is malformed."""
    dates_text = "\n".join(batch_dates)
    last_error = None

    # Retry the same small batch once before splitting it further.
    for attempt in range(2):
        try:
            response = chain.invoke({"place": place, "dates": dates_text})
            raw_text = response.content
            if isinstance(raw_text, list):
                raw_text = "".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in raw_text
                )
            if not raw_text or not str(raw_text).strip():
                raise ValueError("The model returned an empty response.")
            parsed = extract_json(str(raw_text))
            return _normalise_records(parsed, place, batch_dates)
        except Exception as exc:
            last_error = exc

    # A smaller request is more likely to fit within the model's output limit.
    if len(batch_dates) > 1:
        midpoint = len(batch_dates) // 2
        left = generate_batch(place, batch_dates[:midpoint])
        right = generate_batch(place, batch_dates[midpoint:])
        return left + right

    raise RuntimeError(
        f"Could not generate valid data for {batch_dates[0]}. Last error: {last_error}"
    ) from last_error


def generate_pollution_data(place, months, progress_callback=None):
    """
    Generate daily synthetic records for the requested number of calendar months.
    The default six-month period is 1 January through 30 June 2026 (181 records).
    """
    if not isinstance(months, int) or not 1 <= months <= 12:
        raise ValueError("months must be an integer from 1 to 12.")
    if not str(place).strip():
        raise ValueError("Please provide a location.")

    start_date = date(2026, 1, 1)
    # End on the final day of the selected calendar-month range.
    requested_end_date = add_months(start_date, months) - timedelta(days=1)

    batches = create_batches(start_date, requested_end_date, batch_size=10)
    all_records = []
    total_batches = len(batches)

    for index, batch_dates in enumerate(batches):
        records = generate_batch(str(place).strip(), batch_dates)
        all_records.extend(records)

        if progress_callback:
            progress_callback((index + 1) / total_batches)

    # Guard against accidental gaps or duplicates before returning the dataset.
    expected_count = (requested_end_date - start_date).days + 1
    if len(all_records) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} daily records but generated {len(all_records)}."
        )

    return {"data": all_records}


def save_pollution_data(result):
    """Save pollution_data.json in the project root (one level above src/)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "pollution_data.json")

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)

    return file_path
