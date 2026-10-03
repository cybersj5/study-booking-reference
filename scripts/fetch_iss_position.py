"""Получает текущие координаты МКС и сохраняет их в CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://api.wheretheiss.at/v1/satellites/25544"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "iss_positions.csv"


@dataclass(frozen=True)
class IssPosition:
    timestamp: int
    longitude: float
    latitude: float


def parse_position(payload: dict[str, Any]) -> IssPosition:
    """Проверка ответа здесь защищает CSV от неполных или ошибочных данных API."""
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
        raise ValueError("В ответе API отсутствует timestamp")

    try:
        longitude = float(payload["longitude"])
        latitude = float(payload["latitude"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Координаты API имеют неверный формат") from error

    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise ValueError("Координаты API выходят за допустимый диапазон")

    return IssPosition(
        timestamp=int(timestamp),
        longitude=longitude,
        latitude=latitude,
    )


def fetch_position(timeout_seconds: float = 10) -> IssPosition:
    request = Request(API_URL, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)

    if not isinstance(payload, dict):
        raise ValueError("API вернул JSON неожиданного формата")

    return parse_position(payload)


def append_position(output_path: Path, position: IssPosition) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not output_path.exists() or output_path.stat().st_size == 0

    with output_path.open("a", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["timestamp", "longitude", "latitude"],
        )
        if needs_header:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": position.timestamp,
                "longitude": position.longitude,
                "latitude": position.latitude,
            }
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Получить координаты МКС и дописать их в CSV-файл.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Путь к CSV-файлу (по умолчанию: {DEFAULT_OUTPUT})",
    )
    return parser


def main() -> int:
    arguments = build_argument_parser().parse_args()

    try:
        position = fetch_position()
        append_position(arguments.output, position)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        print(f"Не удалось получить координаты МКС: {error}", file=sys.stderr)
        return 1

    print(
        f"Сохранено: timestamp={position.timestamp}, "
        f"longitude={position.longitude}, latitude={position.latitude}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
