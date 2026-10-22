import json
import os
import re
from datetime import date, timedelta

from dotenv import load_dotenv

from langchain_huggingface import (
    ChatHuggingFace,
    HuggingFaceEndpoint
)

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser


load_dotenv()

token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

if not token:
    raise ValueError(
        "HUGGINGFACEHUB_API_TOKEN not found in .env file"
    )


llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    task="text-generation",
    huggingfacehub_api_token=token,
    provider="featherless-ai"
)

model = ChatHuggingFace(
    llm=llm
)

parser = JsonOutputParser()


template = PromptTemplate(
    template="""

Generate synthetic pollution data.

Location: {place}

Dates:
{dates}

Return a JSON object in exactly this format:

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

- Create exactly one object for every date.
- Do not skip dates.
- Do not repeat dates.
- Use the exact dates provided.
- Use the exact location provided.
- All pollution values must be numbers.
- Return ONLY JSON.
- Do not use markdown.
- Do not write explanations.

""",
    input_variables=[
        "place",
        "dates"
    ]
)


chain = template | model


def create_batches(start_date, end_date):

    batches = []

    current_date = start_date

    while current_date <= end_date:

        batch = []

        for _ in range(30):

            if current_date > end_date:
                break

            batch.append(
                current_date.strftime("%Y-%m-%d")
            )

            current_date += timedelta(days=1)

        if batch:
            batches.append(batch)

    return batches


def extract_json(text):

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    )

    text = text.strip()

    start = text.find("{")

    end = text.rfind("}")

    if start == -1 or end == -1:

        start = text.find("[")

        end = text.rfind("]")

        if start == -1 or end == -1:

            raise Exception(
                "No JSON found in model response."
            )

    json_text = text[start:end + 1]

    return json.loads(
        json_text
    )


def generate_batch(
    place,
    batch_dates
):

    dates_text = "\n".join(
        batch_dates
    )

    response = chain.invoke(
        {
            "place": place,
            "dates": dates_text
        }
    )

    raw_text = response.content

    if not raw_text:

        raise Exception(
            "The model returned an empty response."
        )

    try:

        parsed = extract_json(
            raw_text
        )

    except Exception as e:

        raise Exception(
            "Could not parse model response as JSON. "
            f"Model response: {raw_text[:500]}"
        ) from e

    if isinstance(
        parsed,
        dict
    ):

        generated = parsed.get(
            "data",
            []
        )

    elif isinstance(
        parsed,
        list
    ):

        generated = parsed

    else:

        generated = []

    if not generated:

        raise Exception(
            "The model returned no records."
        )

    generated_by_date = {}

    for record in generated:

        if not isinstance(
            record,
            dict
        ):
            continue

        record_date = record.get(
            "date"
        )

        if record_date:

            generated_by_date[
                record_date
            ] = record

    missing_dates = [
        current_date
        for current_date in batch_dates
        if current_date not in generated_by_date
    ]

    if missing_dates:

        raise Exception(
            "Model missed these dates: "
            + ", ".join(missing_dates)
        )

    records = []

    for current_date in batch_dates:

        record = generated_by_date[
            current_date
        ]

        record["location"] = place

        records.append(
            record
        )

    return records


def generate_pollution_data(
    place,
    months,
    progress_callback=None
):

    start_date = date(
        2026,
        1,
        1
    )

    today = date.today()

    requested_end_date = (
        start_date
        + timedelta(
            days=(months * 30) - 1
        )
    )

    if requested_end_date > today:

        requested_end_date = today

    batches = create_batches(
        start_date,
        requested_end_date
    )

    all_records = []

    total_batches = len(
        batches
    )

    for index, batch_dates in enumerate(
        batches
    ):

        records = generate_batch(
            place,
            batch_dates
        )

        all_records.extend(
            records
        )

        if progress_callback:

            progress_callback(
                (index + 1)
                / total_batches
            )

    return {
        "data": all_records
    }


def save_pollution_data(
    result
):

    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    file_path = os.path.join(
        base_dir,
        "pollution_data.json"
    )

    with open(
        file_path,
        "w"
    ) as f:

        json.dump(
            result,
            f,
            indent=4
        )

    return file_path