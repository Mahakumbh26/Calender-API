"""
calendar_engine.py
Computes Panchang + state-wise Indian festivals dynamically.
- Lunar festivals: derived from lunar_month + tithi + nakshatra (accurate any year)
- Solar festivals: fixed by solar/Gregorian calendar (correct to be static)
- Gazetted holidays: via `holidays` library
"""

from datetime import datetime
import math
import ephem
import holidays as holidays_lib

# ── Panchang tables ───────────────────────────────────────────────────────────

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

ALL_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu & Kashmir", "Ladakh", "Puducherry",
    "Chandigarh", "Andaman & Nicobar", "Lakshadweep", "Dadra & Nagar Haveli"
]

# ── Lunar festival rules ──────────────────────────────────────────────────────
# Key: (lunar_month 0-11, tithi 0-29, nakshatra 0-26 or None)
# Value: dict { state_name: festival_name }
# "All India" means every state gets it

ALL_INDIA = {s: None for s in ALL_STATES}  # placeholder, filled per rule

def _all(name):
    """Returns {state: name} for every state."""
    return {s: name for s in ALL_STATES}

def _states(name, *states):
    """Returns {state: name} for given states only."""
    return {s: name for s in states}

LUNAR_FESTIVAL_RULES = {
    # ── Chaitra (0) ──────────────────────────────────────────────────────────
    (0, 0, None): {
        **_states("Gudi Padwa", "Maharashtra", "Goa", "Dadra & Nagar Haveli"),
        **_states("Ugadi", "Karnataka", "Andhra Pradesh", "Telangana"),
        **_states("Cheti Chand", "Rajasthan", "Gujarat", "Delhi"),
        **_states("Navreh", "Jammu & Kashmir"),
        **_states("Sajibu Nongma Panba", "Manipur"),
    },
    (0, 8, None): _all("Ram Navami"),
    (0, 13, None): _all("Mahavir Jayanti"),
    (0, 14, None): _all("Hanuman Jayanti"),

    # ── Vaishakha (1) ────────────────────────────────────────────────────────
    (1, 2, None): _all("Akshaya Tritiya"),
    (1, 9, None): _states("Sita Navami", "Uttar Pradesh", "Bihar", "Jharkhand",
                           "Madhya Pradesh", "Uttarakhand"),
    (1, 14, None): {
        **_all("Buddha Purnima"),
        **_states("Narasimha Jayanti", "Andhra Pradesh", "Telangana", "Karnataka"),
    },

    # ── Jyeshtha (2) ─────────────────────────────────────────────────────────
    (2, 9, None): _states("Ganga Dussehra", "Uttar Pradesh", "Uttarakhand",
                           "Bihar", "Jharkhand", "Delhi"),
    (2, 10, None): _states("Vat Savitri Puja", "Maharashtra", "Gujarat",
                            "Bihar", "Jharkhand", "Uttar Pradesh"),
    (2, 14, None): _states("Vat Purnima", "Maharashtra", "Gujarat", "Goa"),
    (2, 28, None): _all("Shani Jayanti"),

    # ── Ashadha (3) ──────────────────────────────────────────────────────────
    (3, 1, None): {
        **_all("Jagannath Rath Yatra"),
        **_states("Rath Yatra (State Holiday)", "Odisha"),
    },
    (3, 10, None): {
        **_all("Devshayani Ekadashi"),
        **_states("Ashadhi Ekadashi", "Maharashtra", "Goa"),
    },
    (3, 14, None): _all("Guru Purnima"),

    # ── Shravana (4) ─────────────────────────────────────────────────────────
    (4, 3, None): _states("Hariyali Teej", "Rajasthan", "Uttar Pradesh",
                           "Haryana", "Punjab", "Delhi", "Madhya Pradesh",
                           "Bihar", "Uttarakhand"),
    (4, 4, None): _all("Nag Panchami"),
    (4, 9, None): _all("Putrada Ekadashi"),
    (4, 14, None): {
        **_all("Raksha Bandhan"),
        **_states("Narali Purnima", "Maharashtra", "Goa"),
        **_states("Avani Avittam", "Tamil Nadu", "Kerala", "Puducherry"),
        **_states("Jhulan Purnima", "West Bengal", "Odisha"),
    },
    (4, 22, None): _states("Kajari Teej", "Madhya Pradesh", "Uttar Pradesh",
                            "Bihar", "Rajasthan"),
    (4, 23, None): _all("Krishna Janmashtami"),

    # ── Bhadrapada (5) ───────────────────────────────────────────────────────
    (5, 3, None): {
        **_all("Ganesh Chaturthi"),
        **_states("Vinayaka Chaturthi (State Holiday)", "Maharashtra", "Goa",
                  "Karnataka", "Andhra Pradesh", "Telangana", "Tamil Nadu"),
    },
    (5, 7, None): _all("Radha Ashtami"),
    (5, 13, None): {
        **_all("Anant Chaturdashi"),
        **_states("Ganesh Visarjan (State Holiday)", "Maharashtra", "Goa"),
    },
    (5, 29, None): _all("Mahalaya Amavasya / Pitru Paksha ends"),

    # ── Ashwin (6) ───────────────────────────────────────────────────────────
    (6, 0, None): _all("Shardiya Navratri begins / Ghatasthapana"),
    (6, 5, None): {
        **_states("Saraswati Puja", "West Bengal", "Odisha", "Assam",
                  "Tripura", "Bihar", "Jharkhand"),
        **_states("Ayudha Puja", "Karnataka", "Tamil Nadu", "Andhra Pradesh",
                  "Telangana", "Kerala"),
    },
    (6, 7, None): _all("Durga Ashtami / Maha Ashtami"),
    (6, 8, None): {
        **_all("Maha Navami"),
        **_states("Ayudha Puja", "Karnataka", "Tamil Nadu", "Andhra Pradesh",
                  "Telangana", "Kerala", "Puducherry"),
    },
    (6, 9, None): {
        **_all("Dussehra / Vijayadashami"),
        **_states("Mysuru Dasara (State Festival)", "Karnataka"),
        **_states("Kullu Dussehra", "Himachal Pradesh"),
        **_states("Bastar Dussehra", "Chhattisgarh"),
    },
    (6, 14, None): {
        **_all("Sharad Purnima / Kojagiri Purnima"),
        **_states("Lakshmi Puja", "West Bengal", "Odisha", "Assam", "Tripura"),
        **_states("Valmiki Jayanti", "Punjab", "Haryana", "Delhi", "Uttar Pradesh"),
    },

    # ── Kartik (7) ───────────────────────────────────────────────────────────
    (7, 3, None): _states("Karva Chauth", "Rajasthan", "Uttar Pradesh",
                           "Punjab", "Haryana", "Delhi", "Himachal Pradesh",
                           "Madhya Pradesh", "Uttarakhand", "Bihar"),
    (7, 7, None): _states("Ahoi Ashtami", "Uttar Pradesh", "Rajasthan",
                           "Haryana", "Punjab", "Delhi", "Madhya Pradesh"),
    (7, 12, None): _all("Dhanteras / Dhanvantari Jayanti"),
    (7, 13, None): {
        **_all("Narak Chaturdashi / Choti Diwali"),
        **_states("Kali Puja", "West Bengal", "Assam", "Odisha", "Tripura"),
    },
    (7, 29, None): {
        **_all("Diwali / Lakshmi Puja"),
        **_states("Kali Puja (State Holiday)", "West Bengal", "Assam",
                  "Odisha", "Tripura"),
    },
    (7, 15, None): {
        **_all("Govardhan Puja / Annakut"),
        **_states("Padwa", "Maharashtra", "Goa"),
        **_states("Bali Pratipada", "Karnataka", "Andhra Pradesh", "Telangana"),
    },
    (7, 16, None): _all("Bhai Dooj / Bhau Beej"),
    (7, 19, None): _states("Chhath Puja - Nahay Khay",
                            "Bihar", "Jharkhand", "Uttar Pradesh",
                            "Delhi", "West Bengal", "Assam"),
    (7, 21, None): _states("Chhath Puja - Sandhya Arghya",
                            "Bihar", "Jharkhand", "Uttar Pradesh",
                            "Delhi", "West Bengal", "Assam"),
    (7, 22, None): _states("Chhath Puja - Usha Arghya",
                            "Bihar", "Jharkhand", "Uttar Pradesh",
                            "Delhi", "West Bengal", "Assam"),
    (7, 25, None): {
        **_all("Dev Uthani Ekadashi / Tulsi Vivah"),
        **_states("Kartik Ekadashi", "Maharashtra", "Goa"),
    },
    (7, 14, None): {
        **_all("Kartik Purnima / Dev Deepawali"),
        **_states("Guru Nanak Jayanti", "Punjab", "Haryana", "Delhi",
                  "Himachal Pradesh", "Uttarakhand", "Chandigarh"),
        **_states("Pushkar Fair", "Rajasthan"),
        **_states("Tripuri Purnima", "Tripura"),
    },

    # ── Margashirsha (8) ─────────────────────────────────────────────────────
    (8, 4, None): _states("Vivah Panchami", "Uttar Pradesh", "Bihar",
                           "Madhya Pradesh", "Rajasthan", "Uttarakhand"),
    (8, 10, None): _all("Mokshada Ekadashi / Gita Jayanti"),
    (8, 14, None): _states("Dattatreya Jayanti", "Maharashtra", "Karnataka",
                            "Goa", "Andhra Pradesh", "Telangana"),

    # ── Paush (9) ────────────────────────────────────────────────────────────
    (9, 14, None): _all("Paush Purnima"),
    (9, 28, None): _all("Masik Shivratri"),

    # ── Magha (10) ───────────────────────────────────────────────────────────
    (10, 4, None): {
        **_all("Vasant Panchami"),
        **_states("Saraswati Puja (State Holiday)", "West Bengal", "Odisha",
                  "Assam", "Bihar", "Jharkhand", "Tripura"),
        **_states("Shri Panchami", "West Bengal", "Odisha"),
    },
    (10, 9, None): _all("Jaya Ekadashi"),
    (10, 14, None): {
        **_all("Maghi Purnima"),
        **_states("Magha Mela", "Uttar Pradesh", "Uttarakhand"),
        **_states("Maghi (State Holiday)", "Punjab", "Haryana", "Chandigarh"),
    },
    (10, 28, None): _all("Maha Shivratri"),

    # ── Phalguna (11) ────────────────────────────────────────────────────────
    (11, 4, None): _states("Rang Panchami", "Maharashtra", "Madhya Pradesh",
                            "Rajasthan", "Gujarat"),
    (11, 9, None): _all("Amalaki Ekadashi"),
    (11, 13, None): _all("Holika Dahan"),
    (11, 14, None): {
        **_all("Holi"),
        **_states("Dol Jatra / Dol Purnima", "West Bengal", "Odisha",
                  "Assam", "Tripura"),
        **_states("Shigmo", "Goa"),
        **_states("Yaosang", "Manipur"),
    },
    (11, 15, None): _states("Dhuleti / Rangwali Holi",
                             "Gujarat", "Rajasthan", "Madhya Pradesh",
                             "Uttar Pradesh", "Bihar"),
}

# ── Solar / harvest / state-formation festivals ───────────────────────────────
# These follow the solar/Gregorian calendar — static is genuinely correct here.
# Value: dict { state: festival_name }

SOLAR_FESTIVALS = {
    (1, 1):   _all("New Year's Day"),
    (1, 14):  {
        **_all("Makar Sankranti"),
        **_states("Pongal (State Holiday)", "Tamil Nadu", "Puducherry"),
        **_states("Lohri", "Punjab", "Haryana", "Himachal Pradesh",
                  "Delhi", "Chandigarh", "Jammu & Kashmir"),
        **_states("Uttarayan / Kite Festival", "Gujarat"),
        **_states("Magh Bihu / Bhogali Bihu", "Assam"),
        **_states("Khichdi Parva", "Uttar Pradesh", "Bihar", "Jharkhand"),
        **_states("Makara Vilakku", "Kerala"),
    },
    (1, 15):  _states("Thiruvalluvar Day", "Tamil Nadu", "Puducherry"),
    (1, 16):  _states("Uzhavar Thirunal / Mattu Pongal", "Tamil Nadu", "Puducherry"),
    (1, 26):  _all("Republic Day"),
    (2, 19):  _states("Chhatrapati Shivaji Maharaj Jayanti", "Maharashtra", "Goa"),
    (3, 22):  _states("Bihar Diwas", "Bihar", "Jharkhand"),
    (4, 14):  {
        **_all("Dr. Ambedkar Jayanti"),
        **_states("Baisakhi / Vaisakhi", "Punjab", "Haryana", "Himachal Pradesh",
                  "Delhi", "Chandigarh", "Uttarakhand"),
        **_states("Puthandu / Tamil New Year", "Tamil Nadu", "Puducherry"),
        **_states("Vishu", "Kerala", "Lakshadweep"),
        **_states("Bohag Bihu / Rongali Bihu", "Assam"),
        **_states("Pohela Boishakh / Bengali New Year", "West Bengal", "Tripura",
                  "Assam"),
        **_states("Himachal Day", "Himachal Pradesh"),
    },
    (4, 15):  _states("Himachal Pradesh Foundation Day", "Himachal Pradesh"),
    (5, 1):   {
        **_states("Maharashtra Day", "Maharashtra", "Goa",
                  "Dadra & Nagar Haveli"),
        **_states("Gujarat Day", "Gujarat"),
        **_all("International Labour Day"),
    },
    (5, 16):  _states("Sikkim Statehood Day", "Sikkim"),
    (6, 1):   _states("Telangana Formation Day", "Telangana"),
    (6, 15):  _states("Maharana Pratap Jayanti", "Rajasthan", "Haryana",
                       "Himachal Pradesh", "Uttar Pradesh"),
    (8, 15):  _all("Independence Day"),
    (9, 5):   _all("Teachers Day"),
    (10, 2):  _all("Gandhi Jayanti"),
    (10, 24): _states("Jammu & Kashmir Accession Day", "Jammu & Kashmir", "Ladakh"),
    (11, 1):  {
        **_states("Karnataka Rajyotsava", "Karnataka"),
        **_states("Haryana Day", "Haryana", "Chandigarh"),
        **_states("Punjab Day", "Punjab", "Chandigarh"),
        **_states("MP Foundation Day", "Madhya Pradesh", "Chhattisgarh"),
        **_states("Kerala Piravi", "Kerala", "Lakshadweep"),
    },
    (11, 9):  _states("Uttarakhand Foundation Day", "Uttarakhand"),
    (11, 15): {
        **_states("Jharkhand Foundation Day", "Jharkhand"),
        **_states("Birsa Munda Jayanti", "Jharkhand", "Odisha", "West Bengal",
                  "Chhattisgarh"),
    },
    (12, 2):  _states("Mizoram Statehood Day", "Mizoram"),
    (12, 3):  _states("Nagaland Statehood Day", "Nagaland"),
    (12, 19): _states("Goa Liberation Day", "Goa", "Dadra & Nagar Haveli"),
    (12, 25): _all("Christmas"),
}


# ── Astronomy helpers ─────────────────────────────────────────────────────────

def _get_ayanamsa(jd: float) -> float:
    T = (jd - 2451545.0) / 36525.0
    return 23.85 + 50.3 * T / 3600.0


def _compute_panchang(year: int, month: int, day: int):
    ephem_date = ephem.Date(f"{year}/{month}/{day} 00:30:00")
    sun  = ephem.Sun(ephem_date)
    moon = ephem.Moon(ephem_date)

    sun_ecl  = math.degrees(ephem.Ecliptic(sun,  epoch=ephem_date).lon)
    moon_ecl = math.degrees(ephem.Ecliptic(moon, epoch=ephem_date).lon)

    jd   = float(ephem_date) + 2415020.0
    ayan = _get_ayanamsa(jd)

    sun_sid  = (sun_ecl  - ayan) % 360.0
    moon_sid = (moon_ecl - ayan) % 360.0

    diff              = (moon_ecl - sun_ecl) % 360.0
    tithi_index       = int(diff / 12.0) % 30
    nakshatra_index   = int(moon_sid / (360.0 / 27)) % 27
    lunar_month_index = int(sun_sid / 30.0) % 12

    return tithi_index, nakshatra_index, lunar_month_index


def _build_state_festivals(tithi_index, nakshatra_index, lunar_month_index, d):
    """
    Returns dict: { state_name: [festival, ...] } for all states.
    Only states with festivals on this date have non-empty lists.
    """
    state_map = {s: [] for s in ALL_STATES}

    # 1. Lunar festivals
    key = (lunar_month_index, tithi_index, None)
    if key in LUNAR_FESTIVAL_RULES:
        for state, name in LUNAR_FESTIVAL_RULES[key].items():
            if name and state in state_map:
                state_map[state].append(name)

    # 2. Solar festivals
    solar_key = (d.month, d.day)
    if solar_key in SOLAR_FESTIVALS:
        for state, name in SOLAR_FESTIVALS[solar_key].items():
            if name and state in state_map:
                if name not in state_map[state]:
                    state_map[state].append(name)

    # 3. Gazetted national holidays (apply to all states)
    india_hols = holidays_lib.India(years=d.year)
    official   = india_hols.get(d)
    if official:
        for state in ALL_STATES:
            if official not in state_map[state]:
                state_map[state].append(official)

    return state_map


# ── Public API ────────────────────────────────────────────────────────────────

def get_calendar_data(date_str: str, state: str = None) -> dict:
    """
    Returns Panchang + state-wise festivals for a given date (YYYY-MM-DD).
    If state is provided, returns festivals only for that state.
    """
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    tithi_index, nakshatra_index, lunar_month_index = _compute_panchang(
        d.year, d.month, d.day
    )

    tithi_name       = f"{PAKSHA[tithi_index]} {TITHI_NAMES[tithi_index]}"
    nakshatra_name   = NAKSHATRAS[nakshatra_index]
    lunar_month_name = LUNAR_MONTH_NAMES[lunar_month_index]

    state_festivals = _build_state_festivals(
        tithi_index, nakshatra_index, lunar_month_index, d
    )

    # Filter to requested state if provided
    if state:
        matched = next((s for s in ALL_STATES if s.lower() == state.lower()), None)
        if not matched:
            raise ValueError(f"Unknown state: {state}")
        state_festivals = {matched: state_festivals[matched]}

    # All unique festivals across all states (for top-level summary)
    all_unique = []
    seen = set()
    for fests in state_festivals.values():
        for f in fests:
            if f not in seen:
                seen.add(f)
                all_unique.append(f)

    # Only include states that have at least one festival
    active_states = {s: v for s, v in state_festivals.items() if v}

    day_of_week = d.weekday()

    return {
        "date": date_str,
        "lunar_month": lunar_month_name,
        "tithi": tithi_name,
        "nakshatra": nakshatra_name,
        "festivals_today": all_unique,
        "state_festivals": active_states,
        "features": {
            "day_of_week": day_of_week,
            "month": d.month,
            "is_weekend": 1 if day_of_week >= 5 else 0,
            "is_holiday": 1 if all_unique else 0,
            "festival_count": len(all_unique),
        },
    }
