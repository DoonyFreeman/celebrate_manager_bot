import logging
from datetime import date

import httpx

from config import settings
from db.models import Holiday
from db.repository import HolidayRepository

logger = logging.getLogger(__name__)

CALENDARIFIC_API_URL = "https://calendarific.com/api/v2/holidays"

CATEGORY_MAP: dict[str, str] = {
    "National holiday": "national",
    "Federal holiday": "national",
    "Observance": "observance",
    "Seasonal observance": "seasonal",
    "Common local holiday": "local",
    "Local holiday": "local",
    "Christian": "religious",
    "Muslim": "religious",
    "Jewish": "religious",
    "Hindu": "religious",
    "Buddhist": "religious",
    "Orthodox": "religious",
}


def _map_category(holiday_types: list[str]) -> str:
    for t in holiday_types:
        mapped = CATEGORY_MAP.get(t)
        if mapped is not None:
            return mapped
    return "other"


async def _fetch_month_holidays(year: int, month: int) -> list[Holiday]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            CALENDARIFIC_API_URL,
            params={
                "api_key": settings.calendarific_api_key,
                "country": settings.country,
                "year": year,
                "month": month,
            },
        )
        response.raise_for_status()
        data = response.json()

    holidays: list[Holiday] = []
    for item in data.get("response", {}).get("holidays", []):
        try:
            holiday_date = date.fromisoformat(item["date"]["iso"])
        except (KeyError, ValueError):
            continue

        holiday_types = item.get("type", [])
        category = _map_category(holiday_types)

        holidays.append(
            Holiday(
                id=None,
                date=holiday_date,
                name=item["name"],
                category=category,
                description=item.get("description"),
                external_id=str(item.get("id", "")),
            )
        )

    return holidays


async def get_today_holidays() -> list[Holiday]:
    today = date.today()

    if await HolidayRepository.has_cache_for_date(today):
        return await HolidayRepository.get_by_date(today)

    try:
        holidays = await _fetch_month_holidays(today.year, today.month)
        await HolidayRepository.bulk_insert(holidays)
    except httpx.HTTPError:
        logger.exception("Failed to fetch holidays from Calendarific")
        return []

    return await HolidayRepository.get_by_date(today)
