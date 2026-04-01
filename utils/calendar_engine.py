"""
calendar_engine.py
Computes Panchang + all-India state-wise festivals dynamically.
- Lunar festivals: derived from lunar_month + tithi + nakshatra (accurate any year)
- Solar/harvest festivals: fixed by solar calendar (genuinely correct to be static)
- Gazetted holidays: via `holidays` library
"""

from datetime import datetime
import math
import ephem
import holidays as holidays_lib

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya"
]

PAKSHA = (["Shukla"] * 15) + (["Krishna"] * 15)

LUNAR_MONTH_NAMES = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha",
    "Shravana", "Bhadrapada", "Ashwin", "Kartik",
    "Margashirsha", "Paush", "Magha", "Phalguna"
]

# ─────────────────────────────────────────────────────────────────────────────
# LUNAR FESTIVAL RULES
# Key: (lunar_month_index 0-11, tithi_index 0-29, nakshatra_index 0-26 or None)
# Value: list of festival names (with state tags where regional)
# ─────────────────────────────────────────────────────────────────────────────
LUNAR_FESTIVAL_RULES = {
    # ── Chaitra (0) ──────────────────────────────────────────────────────────
    (0,  0, None): ["Gudi Padwa (Maharashtra)", "Ugadi (Karnataka/Andhra/Telangana)",
                    "Cheti Chand (Sindhi New Year)", "Navreh (Kashmiri New Year)"],
    (0,  5, None): ["Yamuna Chhath (UP/Bihar)"],
    (0,  8, None): ["Ram Navami (All India)"],
    (0, 13, None): ["Mahavir Jayanti (Jain)"],
    (0, 14, None): ["Hanuman Jayanti (All India)"],

    # ── Vaishakha (1) ────────────────────────────────────────────────────────
    (1,  2, None): ["Akshaya Tritiya (All India)", "Parashurama Jayanti"],
    (1,  5, None): ["Shankaracharya Jayanti"],
    (1,  9, None): ["Sita Navami (UP/Bihar)"],
    (1, 14, None): ["Buddha Purnima (All India)", "Narasimha Jayanti"],

    # ── Jyeshtha (2) ─────────────────────────────────────────────────────────
    (2,  9, None): ["Ganga Dussehra (UP/Uttarakhand)"],
    (2, 10, None): ["Vat Savitri Puja (Maharashtra/Gujarat/Bihar)"],
    (2, 14, None): ["Vat Purnima (Maharashtra/Gujarat)"],
    (2, 28, None): ["Shani Jayanti (All India)"],
    (2, 29, None): ["Shani Amavasya / Jyeshtha Amavasya"],

    # ── Ashadha (3) ──────────────────────────────────────────────────────────
    (3,  1, None): ["Jagannath Rath Yatra (Odisha/All India)"],
    (3,  5, None): ["Skanda Sashti (Tamil Nadu)"],
    (3, 10, None): ["Devshayani Ekadashi / Ashadhi Ekadashi (Maharashtra)"],
    (3, 14, None): ["Guru Purnima (All India)", "Vyasa Purnima"],

    # ── Shravana (4) ─────────────────────────────────────────────────────────
    (4,  3, None): ["Hariyali Teej (Rajasthan/UP/Haryana)"],
    (4,  4, None): ["Nag Panchami (All India)"],
    (4,  5, None): ["Skanda Sashti (Tamil Nadu)"],
    (4,  9, None): ["Putrada Ekadashi"],
    (4, 13, None): ["Onam begins (Kerala) - Atham day"],
    (4, 14, None): ["Raksha Bandhan / Shravana Purnima (All India)",
                    "Narali Purnima (Maharashtra - Coconut Festival)",
                    "Avani Avittam (Tamil Nadu/Kerala Brahmin)"],
    (4, 22, None): ["Kajari Teej (MP/UP/Bihar)"],
    (4, 23, None): ["Krishna Janmashtami (All India)"],

    # ── Bhadrapada (5) ───────────────────────────────────────────────────────
    (5,  3, None): ["Ganesh Chaturthi (Maharashtra/All India)",
                    "Vinayaka Chaturthi (Tamil Nadu/Andhra/Karnataka)"],
    (5,  5, None): ["Rishi Panchami"],
    (5,  5, 6):    ["Lalita Panchami"],
    (5,  7, None): ["Radha Ashtami (All India)"],
    (5, 12, None): ["Onam Thiruvonam (Kerala) - main day"],
    (5, 13, None): ["Anant Chaturdashi (All India)", "Ganesh Visarjan"],
    (5, 14, None): ["Bhadrapada Purnima"],
    (5, 24, None): ["Indira Ekadashi"],
    (5, 29, None): ["Mahalaya Amavasya / Pitru Paksha ends (All India)"],

    # ── Ashwin (6) ───────────────────────────────────────────────────────────
    (6,  0, None): ["Shardiya Navratri begins / Ghatasthapana (All India)"],
    (6,  5, None): ["Saraswati Puja / Ayudha Puja (Bengal/South India)"],
    (6,  7, None): ["Durga Ashtami / Maha Ashtami (All India)"],
    (6,  8, None): ["Maha Navami (All India)", "Ayudha Puja (Karnataka/Tamil Nadu)"],
    (6,  9, None): ["Dussehra / Vijayadashami (All India)",
                    "Mysuru Dasara (Karnataka)", "Kullu Dussehra (Himachal Pradesh)"],
    (6, 10, None): ["Papankusha Ekadashi"],
    (6, 14, None): ["Kojagiri Purnima / Sharad Purnima (All India)",
                    "Lakshmi Puja (Bengal/Odisha)", "Valmiki Jayanti"],

    # ── Kartik (7) ───────────────────────────────────────────────────────────
    (7,  3, None): ["Karva Chauth (Rajasthan/UP/Punjab/Haryana)"],
    (7,  7, None): ["Ahoi Ashtami (North India)"],
    (7, 10, None): ["Govatsa Dwadashi / Dhanteras eve"],
    (7, 12, None): ["Dhanteras / Dhanvantari Jayanti (All India)"],
    (7, 13, None): ["Narak Chaturdashi / Choti Diwali (All India)",
                    "Kali Puja (Bengal/Assam/Odisha)"],
    (7, 29, None): ["Diwali / Lakshmi Puja (All India)",
                    "Kali Puja (Bengal)", "Naraka Chaturdashi (South India)"],
    (7, 15, None): ["Govardhan Puja / Annakut (All India)", "Padwa (Maharashtra)"],
    (7, 16, None): ["Bhai Dooj / Bhau Beej (All India)", "Yama Dwitiya"],
    (7, 19, None): ["Chhath Puja begins (Bihar/UP/Jharkhand)"],
    (7, 21, None): ["Chhath Puja - Sandhya Arghya (Bihar/UP/Jharkhand)"],
    (7, 22, None): ["Chhath Puja - Usha Arghya (Bihar/UP/Jharkhand)"],
    (7, 25, None): ["Dev Uthani Ekadashi / Tulsi Vivah (All India)"],
    (7, 14, None): ["Kartik Purnima / Dev Deepawali (Varanasi/All India)",
                    "Guru Nanak Jayanti (Punjab/All India)",
                    "Pushkar Fair (Rajasthan)"],

    # ── Margashirsha (8) ─────────────────────────────────────────────────────
    (8,  4, None): ["Vivah Panchami (UP/Bihar - Ram-Sita marriage)"],
    (8, 10, None): ["Mokshada Ekadashi / Gita Jayanti (All India)"],
    (8, 14, None): ["Dattatreya Jayanti (Maharashtra/Karnataka)"],

    # ── Paush (9) ────────────────────────────────────────────────────────────
    (9,  5, None): ["Saphala Ekadashi"],
    (9, 10, None): ["Paush Putrada Ekadashi"],
    (9, 14, None): ["Paush Purnima / Shakambhari Purnima"],
    (9, 28, None): ["Masik Shivratri"],

    # ── Magha (10) ───────────────────────────────────────────────────────────
    (10,  4, None): ["Vasant Panchami / Saraswati Puja (All India)",
                     "Shri Panchami (Bengal/Odisha)"],
    (10,  9, None): ["Jaya Ekadashi"],
    (10, 14, None): ["Maghi Purnima (Punjab/All India)", "Magha Mela (Prayagraj)"],
    (10, 28, None): ["Maha Shivratri (All India)"],

    # ── Phalguna (11) ────────────────────────────────────────────────────────
    (11,  4, None): ["Rang Panchami (Maharashtra/MP)"],
    (11,  9, None): ["Amalaki Ekadashi"],
    (11, 13, None): ["Holika Dahan / Holi eve (All India)"],
    (11, 14, None): ["Holi / Dhulandi (All India)", "Shigmo (Goa)",
                     "Dol Jatra / Dol Purnima (Bengal/Odisha/Assam)"],
    (11, 15, None): ["Rangwali Holi / Dhuleti (Gujarat/Rajasthan)"],
}

# Nakshatra-specific festivals (lunar_month, tithi, nakshatra): names
NAKSHATRA_FESTIVAL_RULES = {
    # Pushya nakshatra festivals
    (7, 14, 7):  ["Pushya Nakshatra Purnima (auspicious for gold buying)"],
    # Shravana nakshatra
    (4, 14, 21): ["Shravana Purnima with Shravana Nakshatra (extra auspicious)"],
    # Rohini nakshatra - Janmashtami
    (4, 23, 3):  ["Krishna Janmashtami - Rohini Nakshatra (most auspicious)"],
    # Magha nakshatra
    (10, 14, 9): ["Maghi Purnima with Magha Nakshatra"],
    # Vishakha nakshatra
    (0, 14, 15): ["Hanuman Jayanti with Vishakha Nakshatra"],
}

# ─────────────────────────────────────────────────────────────────────────────
# SOLAR / HARVEST FESTIVALS (genuinely fixed by solar calendar)
# These are correctly static — they follow the Gregorian/solar calendar
# ─────────────────────────────────────────────────────────────────────────────
SOLAR_FESTIVALS = {
    # National
    (1,  1):  ["New Year's Day"],
    (1, 26):  ["Republic Day"],
    (8, 15):  ["Independence Day"],
    (10, 2):  ["Gandhi Jayanti"],
    (12, 25): ["Christmas"],

    # Solar harvest & regional new years (solar calendar based)
    (1, 14):  ["Makar Sankranti (All India)", "Pongal (Tamil Nadu)",
               "Lohri (Punjab/Haryana)", "Uttarayan (Gujarat)",
               "Magh Bihu (Assam)", "Khichdi Parva (UP/Bihar)"],
    (1, 15):  ["Thiruvalluvar Day (Tamil Nadu)", "Mattu Pongal (Tamil Nadu)"],
    (1, 16):  ["Kannum Pongal (Tamil Nadu)"],
    (3, 22):  ["Bihar Diwas (Bihar Foundation Day)"],
    (4, 14):  ["Dr. Ambedkar Jayanti", "Baisakhi (Punjab/Haryana)",
               "Tamil New Year / Puthandu (Tamil Nadu)",
               "Vishu (Kerala)", "Bohag Bihu / Rongali Bihu (Assam)",
               "Pohela Boishakh (Bengal New Year)"],
    (4, 15):  ["Himachal Pradesh Foundation Day"],
    (5,  1):  ["Maharashtra Day", "Gujarat Day", "Labour Day"],
    (6,  1):  ["Telangana Formation Day"],
    (7, 17):  ["Muharram / Islamic New Year (approximate - varies by moon)"],
    (9,  2):  ["Haryana Foundation Day"],
    (10, 1):  ["Karnataka Rajyotsava eve"],
    (11, 1):  ["Karnataka Rajyotsava (Karnataka Formation Day)",
               "Haryana Day", "Punjab Day", "MP Foundation Day",
               "Kerala Piravi (Kerala Formation Day)"],
    (11, 9):  ["Uttarakhand Foundation Day"],
    (11, 15): ["Jharkhand Foundation Day"],
    (12, 19): ["Goa Liberation Day"],
}


def _get_ayanamsa(jd: float) -> float:
    T = (jd - 2451545.0) / 36525.0
    return 23.85 + 50.3 * T / 3600.0


def _compute_panchang(year: int, month: int, day: int):
    """Returns (tithi_index, nakshatra_index, lunar_month_index, sun_sid, moon_sid)"""
    ephem_date = ephem.Date(f"{year}/{month}/{day} 00:30:00")

    sun  = ephem.Sun(ephem_date)
    moon = ephem.Moon(ephem_date)

    sun_ecl  = math.degrees(ephem.Ecliptic(sun,  epoch=ephem_date).lon)
    moon_ecl = math.degrees(ephem.Ecliptic(moon, epoch=ephem_date).lon)

    jd   = float(ephem_date) + 2415020.0
    ayan = _get_ayanamsa(jd)

    sun_sid  = (sun_ecl  - ayan) % 360.0
    moon_sid = (moon_ecl - ayan) % 360.0

    diff            = (moon_ecl - sun_ecl) % 360.0
    tithi_index     = int(diff / 12.0) % 30
    nakshatra_index = int(moon_sid / (360.0 / 27)) % 27
    lunar_month_index = int(sun_sid / 30.0) % 12

    return tithi_index, nakshatra_index, lunar_month_index, sun_sid, moon_sid


def _collect_lunar_festivals(tithi_index, nakshatra_index, lunar_month_index):
    """Return all matching lunar festivals for this panchang combination."""
    results = []

    # Nakshatra-specific rules (most specific, check first)
    nak_key = (lunar_month_index, tithi_index, nakshatra_index)
    if nak_key in NAKSHATRA_FESTIVAL_RULES:
        results.extend(NAKSHATRA_FESTIVAL_RULES[nak_key])

    # General tithi rules
    tithi_key = (lunar_month_index, tithi_index, None)
    if tithi_key in LUNAR_FESTIVAL_RULES:
        results.extend(LUNAR_FESTIVAL_RULES[tithi_key])

    return results


def get_calendar_data(date_str: str) -> dict:
    """
    Returns full Panchang + all-India state-wise festival data for a date (YYYY-MM-DD).
    Lunar festivals computed dynamically — accurate for any year.
    """
    d = datetime.strptime(date_str, "%Y-%m-%d").date()

    tithi_index, nakshatra_index, lunar_month_index, _, _ = _compute_panchang(
        d.year, d.month, d.day
    )

    tithi_name       = f"{PAKSHA[tithi_index]} {TITHI_NAMES[tithi_index]}"
    nakshatra_name   = NAKSHATRAS[nakshatra_index]
    lunar_month_name = LUNAR_MONTH_NAMES[lunar_month_index]

    # 1. Dynamic lunar + nakshatra festivals
    lunar_festivals = _collect_lunar_festivals(tithi_index, nakshatra_index, lunar_month_index)

    # 2. Gazetted national holidays via holidays library
    india_hols   = holidays_lib.India(years=d.year)
    official     = india_hols.get(d)
    official_list = [official] if official else []

    # 3. Solar/harvest/state-formation festivals (correctly static)
    solar_list = SOLAR_FESTIVALS.get((d.month, d.day), [])

    # Merge all, deduplicate preserving order
    all_festivals = lunar_festivals + official_list + solar_list
    seen = set()
    unique = []
    for f in all_festivals:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    day_of_week = d.weekday()
    is_weekend  = 1 if day_of_week >= 5 else 0
    is_holiday  = 1 if unique else 0

    return {
        "date": date_str,
        "lunar_month": lunar_month_name,
        "tithi": tithi_name,
        "nakshatra": nakshatra_name,
        "festivals": unique,                          # full list
        "festival": unique[0] if unique else None,    # primary festival
        "features": {
            "day_of_week": day_of_week,
            "month": d.month,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "festival_count": len(unique),
        },
    }
