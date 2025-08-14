from __future__ import annotations

from datetime import date as dt_date, datetime
from typing import Optional, Union


def get_season(lat: float, date: Optional[Union[dt_date, datetime]] = None) -> str:
    """Return the season ('spring', 'summer', 'autumn', 'winter') for latitude/date."""
    if date is None:
        date = datetime.now().date()
    elif isinstance(date, datetime):
        date = date.date()

    spring_start = (3, 21)
    summer_start = (6, 21)
    autumn_start = (9, 23)
    winter_start = (12, 21)

    if date >= dt_date(date.year, *spring_start) and date < dt_date(date.year, *summer_start):
        season = "spring"
    elif date >= dt_date(date.year, *summer_start) and date < dt_date(date.year, *autumn_start):
        season = "summer"
    elif date >= dt_date(date.year, *autumn_start) and date < dt_date(date.year, *winter_start):
        season = "autumn"
    else:
        if date >= dt_date(date.year, *winter_start) or date < dt_date(date.year, *spring_start):
            season = "winter"
        else:
            season = "winter"

    if lat < 0:
        invert = {"spring": "autumn", "summer": "winter", "autumn": "spring", "winter": "summer"}
        season = invert[season]
    return season



