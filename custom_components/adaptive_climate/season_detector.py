"""
season_detector.py

Utility function to detect the season of the year (spring, summer, autumn, winter)
based on latitude and date, using fixed astronomical dates for equinoxes and solstices.

- Northern hemisphere: standard dates.
- Southern hemisphere: seasons are inverted.

Usage:
    get_season(lat: float, date: Optional[datetime.date | datetime.datetime] = None) -> str

Example:
    >>> get_season(-23.5, date(2025, 7, 5))
    'winter'
"""
from datetime import date as dt_date, datetime
from typing import Optional, Union

def get_season(lat: float, date: Optional[Union[dt_date, datetime]] = None) -> str:
    """
    Returns the season ('spring', 'summer', 'autumn', 'winter') for the given latitude and date.
    Reference dates (northern hemisphere):
        - Spring: 21/03 – 20/06
        - Summer: 21/06 – 22/09
        - Autumn: 23/09 – 20/12
        - Winter: 21/12 – 20/03
    For the southern hemisphere (lat < 0), the seasons are inverted.

    Args:
        lat (float): Latitude (negative for southern hemisphere).
        date (datetime.date | datetime.datetime, optional): Date to consider. If None, uses current date.
    Returns:
        str: Season ('spring', 'summer', 'autumn', 'winter').
    """
    if date is None:
        date = datetime.now().date()
    elif isinstance(date, datetime):
        date = date.date()
    # Reference dates (year doesn't matter, only month and day)
    spring_start = (3, 21)
    summer_start = (6, 21)
    autumn_start = (9, 23)
    winter_start = (12, 21)
    # Check which season it is (northern hemisphere)
    if (date >= dt_date(date.year, *spring_start) and date < dt_date(date.year, *summer_start)):
        season = "spring"
    elif (date >= dt_date(date.year, *summer_start) and date < dt_date(date.year, *autumn_start)):
        season = "summer"
    elif (date >= dt_date(date.year, *autumn_start) and date < dt_date(date.year, *winter_start)):
        season = "autumn"
    else:
        # Winter: from 21/12 to 20/03 of the next year
        # If between 21/12 and 31/12
        if date >= dt_date(date.year, *winter_start):
            season = "winter"
        # If between 01/01 and 20/03
        elif date < dt_date(date.year, *spring_start):
            season = "winter"
        else:
            # Should not happen, but fallback
            season = "winter"
    # Invert for southern hemisphere
    if lat < 0:
        invert = {"spring": "autumn", "summer": "winter", "autumn": "spring", "winter": "summer"}
        season = invert[season]
    return season

if __name__ == "__main__":
    from datetime import date
    print("São Paulo (-23.5), today:", get_season(-23.5))
    print("Milan (45.4), today:", get_season(45.4))
    print("São Paulo (-23.5), 05/07/2025:", get_season(-23.5, date(2025, 7, 5)))
    print("Milan (45.4), 05/07/2025:", get_season(45.4, date(2025, 7, 5)))
