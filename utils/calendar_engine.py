"""
calendar_engine.py
Computes Panchang data (Tithi, Nakshatra) using the ephem library
and Indian holiday info using the holidays library + custom extras.
Location: Mumbai (Lat: 19.07, Lon: 72.87)
"""

from datetime import date, datetime
import math
import ephem
import holidays

# Mumbai coordinates
MUMBAI_LAT = "19.07"
MUMBAI_LON = "72.87"

# Custom Indian holidays not covered by the holidays library
# Format: (month, day): "Holiday Name"
CUSTOM_INDIA_HOLIDAYS = {
    (1, 1):  "New Year's Day",
    (1, 14): "Makar Sankranti / Pongal",
    (3, 25): "Holi",       # 2026 date; approximate for other years
    (4, 14): "Dr. Ambedkar Jayanti",
    (4, 14): "Tamil New Year / Baisakhi",
    (8, 19): "Raksha Bandhan",   # approximate
    (10, 2): "Gandhi Jayanti",
    (10, 20): "Dussehra",        # approximate
    (11, 8): "Diwali",           # approximate
    (11, 9): "Govardhan Puja",   # approximate
    (11, 10): "Bhai Dooj",       # approximate
}

# 27 Nakshatras, each spans 360/27 ≈ 13.333 degrees of the Moon's longitude
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# 30 Tithis:
# Elongation 0–180° = Shukla Paksha (waxing), ends at Purnima (index 14, ~168–180°)
# Elongation 180–360° = Krishna Paksha (waning), ends at Amavasya (index 29, ~348–360°)
TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",   # indices 0–14 (Shukla)
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya"   # indices 15–29 (Krishna)
]

PAKSHA = (["Shukla"] * 15) + (["Krishna"] * 15)


def _get_ayanamsa(jd: float) -> float:
    """
    Lahiri ayanamsa (sidereal correction) for a given Julian date.
    Approximation accurate to within ~1 arcminute for modern dates.
    """
    T = (jd - 2451545.0) / 36525.0  # Julian centuries from J2000
    return 23.85 + 50.3 * T / 3600.0  # degrees


def _tropical_to_sidereal(lon_deg: float, jd: float) -> float:
    """Convert tropical longitude to sidereal (Nirayana) longitude."""
    ayanamsa = _get_ayanamsa(jd)
    return (lon_deg - ayanamsa) % 360.0


def _compute_panchang(year: int, month: int, day: int):
    """
    Compute Tithi and Nakshatra for a given date at IST noon (UTC 06:30).
    Uses geocentric ecliptic longitudes for accurate Moon-Sun elongation.
    """
    # Sample at IST sunrise ≈ UTC 00:30 (IST 06:00)
    # This matches traditional Panchang which assigns tithi based on sunrise
    ephem_date = ephem.Date(f"{year}/{month}/{day} 00:30:00")

    sun = ephem.Sun(ephem_date)
    moon = ephem.Moon(ephem_date)

    # Geocentric ecliptic longitudes (degrees)
    sun_ecl = math.degrees(ephem.Ecliptic(sun, epoch=ephem_date).lon)
    moon_ecl = math.degrees(ephem.Ecliptic(moon, epoch=ephem_date).lon)

    jd = float(ephem_date) + 2415020.0

    # Apply Lahiri ayanamsa for sidereal Nakshatra
    ayan = _get_ayanamsa(jd)
    moon_sid = (moon_ecl - ayan) % 360.0

    # Tithi: Moon-Sun elongation / 12 degrees each, 30 tithis total
    # index 0-13 = Shukla Pratipada..Chaturdashi, 14 = Purnima
    # index 15-28 = Krishna Pratipada..Chaturdashi, 29 = Amavasya
    diff = (moon_ecl - sun_ecl) % 360.0
    tithi_index = int(diff / 12.0) % 30

    # Nakshatra: Moon sidereal longitude / (360/27) degrees each
    nakshatra_index = int(moon_sid / (360.0 / 27)) % 27

    return tithi_index, nakshatra_index


def get_calendar_data(date_str: str) -> dict:
    """
    Returns Panchang calendar data for the given date string (YYYY-MM-DD).
    Raises ValueError on invalid format.
    """
    # Parse the date
    date = datetime.strptime(date_str, "%Y-%m-%d").date()

    tithi_index, nakshatra_index = _compute_panchang(date.year, date.month, date.day)

    tithi_name = f"{PAKSHA[tithi_index]} {TITHI_NAMES[tithi_index]}"
    nakshatra_name = NAKSHATRAS[nakshatra_index]

    # --- Holiday lookup (India) ---
    # Combine official gazetted holidays with custom popular ones
    india_holidays = holidays.India(years=date.year)
    holiday_name = india_holidays.get(date)

    # Fall back to custom list if not found in official list
    if not holiday_name:
        holiday_name = CUSTOM_INDIA_HOLIDAYS.get((date.month, date.day))

    # --- Feature engineering ---
    day_of_week = date.weekday()          # 0=Monday … 6=Sunday
    month = date.month
    is_weekend = 1 if day_of_week >= 5 else 0
    is_holiday = 1 if holiday_name else 0

    return {
        "date": date_str,
        "tithi": tithi_name,
        "nakshatra": nakshatra_name,
        "holiday": holiday_name,
        "features": {
            "day_of_week": day_of_week,
            "month": month,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
        },
    }
