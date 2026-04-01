"""
calendar_engine.py
Kalnirnay-style Panchang engine.
Five angas: Tithi, Vara, Nakshatra, Yoga, Karana
Festival detection:
  - Lunar festivals  → computed from (lunar_month, tithi, nakshatra) — dynamic, any year
  - Solar festivals  → fixed Gregorian date (harvest/solar calendar — correct to be static)
  - Gazetted         → `holidays` library
All 36 states/UTs covered with their local festivals.
"""

from datetime import datetime
import math
import ephem
import holidays as holidays_lib

# ── Panchang lookup tables ────────────────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

TITHI_NAMES = [
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]
PAKSHA = ["Shukla"]*15 + ["Krishna"]*15

YOGA_NAMES = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana",
    "Atiganda","Sukarma","Dhriti","Shula","Ganda",
    "Vriddhi","Dhruva","Vyaghata","Harshana","Vajra",
    "Siddhi","Vyatipata","Variyan","Parigha","Shiva",
    "Siddha","Sadhya","Shubha","Shukla","Brahma",
    "Indra","Vaidhriti"
]

KARANA_NAMES = [
    "Bava","Balava","Kaulava","Taitila","Garaja",
    "Vanija","Vishti","Shakuni","Chatushpada","Naga","Kimstughna"
]

VARA_NAMES = ["Somavar","Mangalavar","Budhavar","Guruvar","Shukravar","Shanivar","Ravivar"]

LUNAR_MONTH_NAMES = [
    "Chaitra","Vaishakha","Jyeshtha","Ashadha",
    "Shravana","Bhadrapada","Ashwin","Kartik",
    "Margashirsha","Paush","Magha","Phalguna"
]

ALL_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar",
    "Chhattisgarh","Goa","Gujarat","Haryana",
    "Himachal Pradesh","Jharkhand","Karnataka","Kerala",
    "Madhya Pradesh","Maharashtra","Manipur","Meghalaya",
    "Mizoram","Nagaland","Odisha","Punjab",
    "Rajasthan","Sikkim","Tamil Nadu","Telangana",
    "Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
    "Delhi","Jammu & Kashmir","Ladakh","Puducherry",
    "Chandigarh","Andaman & Nicobar","Lakshadweep","Dadra & Nagar Haveli"
]


def _all(name):
    return {s: name for s in ALL_STATES}

def _states(name, *states):
    return {s: name for s in states}

def _merge(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out

# ── Lunar festival rules ──────────────────────────────────────────────────────
# Key: (lunar_month 0-11, tithi 0-29)
# Value: {state: festival_name}
# Lunar month index = Sun's sidereal zodiac sign (0=Aries=Chaitra ... 11=Pisces=Phalguna)

LUNAR_RULES = {

    # ════════════════════════════════════════════════════════════════════════
    # CHAITRA (0) — March/April
    # ════════════════════════════════════════════════════════════════════════
    (0, 0): _merge(
        _states("Gudi Padwa", "Maharashtra","Goa","Dadra & Nagar Haveli"),
        _states("Ugadi", "Karnataka","Andhra Pradesh","Telangana"),
        _states("Cheti Chand (Sindhi New Year)", "Rajasthan","Gujarat","Delhi","Madhya Pradesh"),
        _states("Navreh (Kashmiri New Year)", "Jammu & Kashmir","Ladakh"),
        _states("Sajibu Nongma Panba (Meitei New Year)", "Manipur"),
        _states("Chaitra Navratri begins", "Uttar Pradesh","Bihar","Jharkhand",
                "Uttarakhand","Himachal Pradesh","Haryana","Punjab","Rajasthan",
                "Madhya Pradesh","Chhattisgarh","Delhi"),
    ),
    (0, 5): _states("Yamuna Chhath", "Uttar Pradesh","Bihar","Delhi","Uttarakhand"),
    (0, 7): _merge(
        _states("Chaitra Ashtami / Durga Ashtami", "West Bengal","Odisha","Assam","Tripura"),
        _states("Sheetala Ashtami", "Uttar Pradesh","Rajasthan","Haryana","Punjab","Delhi"),
    ),
    (0, 8): _all("Ram Navami"),
    (0, 13): _all("Mahavir Jayanti"),
    (0, 14): _merge(
        _all("Hanuman Jayanti"),
        _states("Chaitra Purnima", "Tamil Nadu","Puducherry","Kerala"),
    ),
    (0, 29): _states("Chaitra Amavasya", "Odisha","West Bengal","Assam"),

    # ════════════════════════════════════════════════════════════════════════
    # VAISHAKHA (1) — April/May
    # ════════════════════════════════════════════════════════════════════════
    (1, 2): _merge(
        _all("Akshaya Tritiya"),
        _states("Parashurama Jayanti", "Kerala","Karnataka","Maharashtra","Goa"),
    ),
    (1, 5): _states("Shankaracharya Jayanti", "Kerala","Karnataka","Tamil Nadu",
                    "Andhra Pradesh","Telangana"),
    (1, 9): _states("Sita Navami", "Uttar Pradesh","Bihar","Jharkhand",
                    "Madhya Pradesh","Uttarakhand","Rajasthan"),
    (1, 14): _merge(
        _all("Buddha Purnima"),
        _states("Narasimha Jayanti", "Andhra Pradesh","Telangana","Karnataka","Tamil Nadu"),
        _states("Vaishakha Purnima", "Odisha","West Bengal"),
    ),

    # ════════════════════════════════════════════════════════════════════════
    # JYESHTHA (2) — May/June
    # ════════════════════════════════════════════════════════════════════════
    (2, 4): _states("Skanda Sashti", "Tamil Nadu","Puducherry","Kerala","Karnataka",
                    "Andhra Pradesh","Telangana"),
    (2, 9): _states("Ganga Dussehra", "Uttar Pradesh","Uttarakhand","Bihar",
                    "Jharkhand","Delhi","Madhya Pradesh","Rajasthan"),
    (2, 10): _merge(
        _states("Vat Savitri Puja", "Maharashtra","Goa","Gujarat","Bihar",
                "Jharkhand","Uttar Pradesh","Madhya Pradesh","Rajasthan"),
        _states("Nirjala Ekadashi", "Uttar Pradesh","Bihar","Rajasthan","Delhi"),
    ),
    (2, 14): _states("Vat Purnima", "Maharashtra","Gujarat","Goa"),
    (2, 28): _all("Shani Jayanti"),
    (2, 29): _states("Jyeshtha Amavasya / Shani Amavasya",
                     "Uttar Pradesh","Bihar","Rajasthan","Madhya Pradesh","Delhi"),

    # ════════════════════════════════════════════════════════════════════════
    # ASHADHA (3) — June/July
    # ════════════════════════════════════════════════════════════════════════
    (3, 1): _merge(
        _all("Jagannath Rath Yatra"),
        _states("Rath Yatra (State Holiday)", "Odisha"),
    ),
    (3, 4): _states("Skanda Sashti", "Tamil Nadu","Puducherry","Andhra Pradesh","Telangana"),
    (3, 10): _merge(
        _all("Devshayani Ekadashi"),
        _states("Ashadhi Ekadashi (Wari)", "Maharashtra","Goa"),
    ),
    (3, 14): _all("Guru Purnima"),
    (3, 29): _states("Ashadha Amavasya / Dakshinayana begins",
                     "Karnataka","Andhra Pradesh","Telangana","Tamil Nadu","Kerala"),

    # ════════════════════════════════════════════════════════════════════════
    # SHRAVANA (4) — July/August
    # ════════════════════════════════════════════════════════════════════════
    (4, 3): _states("Hariyali Teej", "Rajasthan","Uttar Pradesh","Haryana",
                    "Punjab","Delhi","Madhya Pradesh","Bihar","Uttarakhand","Himachal Pradesh"),
    (4, 4): _all("Nag Panchami"),
    (4, 9): _all("Putrada Ekadashi"),
    (4, 12): _states("Onam - Atham (first day)", "Kerala","Lakshadweep"),
    (4, 13): _states("Onam - Chithira", "Kerala","Lakshadweep"),
    (4, 14): _merge(
        _all("Raksha Bandhan"),
        _states("Narali Purnima (Coconut Festival)", "Maharashtra","Goa"),
        _states("Avani Avittam (Upakarma)", "Tamil Nadu","Kerala","Puducherry"),
        _states("Jhulan Purnima / Jhulana Yatra", "West Bengal","Odisha","Assam"),
        _states("Gamha Purnima", "Odisha"),
        _states("Shravana Purnima", "Uttar Pradesh","Bihar","Uttarakhand","Rajasthan"),
    ),
    (4, 20): _states("Onam - Thiruvonam (Main Day)", "Kerala","Lakshadweep"),
    (4, 22): _states("Kajari Teej", "Madhya Pradesh","Uttar Pradesh","Bihar","Rajasthan"),
    (4, 23): _all("Krishna Janmashtami"),
    (4, 24): _states("Nandotsav", "Uttar Pradesh","Rajasthan","Madhya Pradesh"),

    # ════════════════════════════════════════════════════════════════════════
    # BHADRAPADA (5) — August/September
    # ════════════════════════════════════════════════════════════════════════
    (5, 3): _merge(
        _all("Ganesh Chaturthi"),
        _states("Vinayaka Chaturthi (State Holiday)", "Maharashtra","Goa",
                "Karnataka","Andhra Pradesh","Telangana","Tamil Nadu","Puducherry"),
    ),
    (5, 5): _states("Rishi Panchami", "Maharashtra","Gujarat","Rajasthan",
                    "Uttar Pradesh","Bihar","Madhya Pradesh"),
    (5, 7): _all("Radha Ashtami"),
    (5, 10): _states("Khudurukuni Osha", "Odisha"),
    (5, 11): _states("Onam - Thiruvonam (alternate calc)", "Kerala"),
    (5, 13): _merge(
        _all("Anant Chaturdashi"),
        _states("Ganesh Visarjan (State Holiday)", "Maharashtra","Goa"),
    ),
    (5, 14): _states("Bhadrapada Purnima / Purnima Shraddha", "Odisha","West Bengal","Assam"),
    (5, 24): _all("Indira Ekadashi"),
    (5, 29): _merge(
        _all("Mahalaya Amavasya / Pitru Paksha ends"),
        _states("Mahalaya (Durga Puja begins)", "West Bengal","Assam","Odisha","Tripura"),
    ),

    # ════════════════════════════════════════════════════════════════════════
    # ASHWIN (6) — September/October
    # ════════════════════════════════════════════════════════════════════════
    (6, 0): _all("Shardiya Navratri begins / Ghatasthapana"),
    (6, 5): _merge(
        _states("Saraswati Puja / Saraswati Avahan", "West Bengal","Odisha","Assam",
                "Tripura","Bihar","Jharkhand"),
        _states("Ayudha Puja", "Karnataka","Tamil Nadu","Andhra Pradesh",
                "Telangana","Kerala","Puducherry"),
        _states("Lalita Sashti", "Maharashtra","Gujarat"),
    ),
    (6, 6): _states("Saraswati Puja (main day)", "West Bengal","Odisha","Assam","Tripura"),
    (6, 7): _merge(
        _all("Durga Ashtami / Maha Ashtami"),
        _states("Sandhi Puja", "West Bengal","Assam","Tripura"),
    ),
    (6, 8): _merge(
        _all("Maha Navami"),
        _states("Ayudha Puja (State Holiday)", "Karnataka","Tamil Nadu",
                "Andhra Pradesh","Telangana","Kerala","Puducherry"),
        _states("Navami Homa", "West Bengal","Odisha"),
    ),
    (6, 9): _merge(
        _all("Dussehra / Vijayadashami"),
        _states("Mysuru Dasara (State Festival)", "Karnataka"),
        _states("Kullu Dussehra", "Himachal Pradesh"),
        _states("Bastar Dussehra", "Chhattisgarh"),
        _states("Durga Puja Dashami / Sindur Khela", "West Bengal","Assam","Tripura"),
        _states("Kota Dussehra", "Rajasthan"),
    ),
    (6, 10): _all("Papankusha Ekadashi"),
    (6, 14): _merge(
        _all("Sharad Purnima / Kojagiri Purnima"),
        _states("Lakshmi Puja", "West Bengal","Odisha","Assam","Tripura"),
        _states("Valmiki Jayanti", "Punjab","Haryana","Delhi","Uttar Pradesh",
                "Himachal Pradesh","Chandigarh"),
        _states("Kaumudi Mahotsav", "Uttar Pradesh","Bihar"),
    ),

    # ════════════════════════════════════════════════════════════════════════
    # KARTIK (7) — October/November
    # ════════════════════════════════════════════════════════════════════════
    (7, 3): _states("Karva Chauth", "Rajasthan","Uttar Pradesh","Punjab","Haryana",
                    "Delhi","Himachal Pradesh","Madhya Pradesh","Uttarakhand",
                    "Bihar","Jammu & Kashmir","Chandigarh"),
    (7, 7): _states("Ahoi Ashtami", "Uttar Pradesh","Rajasthan","Haryana",
                    "Punjab","Delhi","Madhya Pradesh","Himachal Pradesh"),
    (7, 10): _states("Govatsa Dwadashi / Vasu Baras", "Maharashtra","Gujarat","Goa"),
    (7, 12): _merge(
        _all("Dhanteras / Dhanvantari Jayanti"),
        _states("Yama Deepam", "Tamil Nadu","Andhra Pradesh","Telangana","Karnataka"),
    ),
    (7, 13): _merge(
        _all("Narak Chaturdashi / Choti Diwali"),
        _states("Kali Puja", "West Bengal","Assam","Odisha","Tripura"),
        _states("Hanuman Puja", "Uttar Pradesh","Bihar","Rajasthan"),
    ),
    (7, 29): _merge(
        _all("Diwali / Lakshmi Puja"),
        _states("Kali Puja (State Holiday)", "West Bengal","Assam","Odisha","Tripura"),
        _states("Naraka Chaturdashi (South)", "Tamil Nadu","Karnataka",
                "Andhra Pradesh","Telangana","Kerala","Puducherry"),
    ),
    (7, 15): _merge(
        _all("Govardhan Puja / Annakut"),
        _states("Padwa / Bali Pratipada", "Maharashtra","Goa"),
        _states("Bali Pratipada", "Karnataka","Andhra Pradesh","Telangana"),
        _states("Gujarati New Year", "Gujarat"),
    ),
    (7, 16): _all("Bhai Dooj / Bhau Beej / Yama Dwitiya"),
    (7, 19): _states("Chhath Puja - Nahay Khay",
                     "Bihar","Jharkhand","Uttar Pradesh","Delhi",
                     "West Bengal","Assam","Uttarakhand"),
    (7, 20): _states("Chhath Puja - Kharna",
                     "Bihar","Jharkhand","Uttar Pradesh","Delhi",
                     "West Bengal","Assam","Uttarakhand"),
    (7, 21): _states("Chhath Puja - Sandhya Arghya (Sunset)",
                     "Bihar","Jharkhand","Uttar Pradesh","Delhi",
                     "West Bengal","Assam","Uttarakhand"),
    (7, 22): _states("Chhath Puja - Usha Arghya (Sunrise)",
                     "Bihar","Jharkhand","Uttar Pradesh","Delhi",
                     "West Bengal","Assam","Uttarakhand"),
    (7, 25): _merge(
        _all("Dev Uthani Ekadashi / Tulsi Vivah"),
        _states("Kartik Ekadashi (Wari)", "Maharashtra","Goa"),
    ),
    (7, 14): _merge(
        _all("Kartik Purnima / Dev Deepawali"),
        _states("Guru Nanak Jayanti", "Punjab","Haryana","Delhi","Himachal Pradesh",
                "Uttarakhand","Chandigarh","Jammu & Kashmir"),
        _states("Pushkar Fair", "Rajasthan"),
        _states("Tripuri Purnima", "Tripura"),
        _states("Kartik Purnima Snan (Ganga)", "Uttar Pradesh","Bihar","Uttarakhand"),
    ),

    # ════════════════════════════════════════════════════════════════════════
    # MARGASHIRSHA (8) — November/December
    # ════════════════════════════════════════════════════════════════════════
    (8, 4): _states("Vivah Panchami (Ram-Sita marriage)", "Uttar Pradesh","Bihar",
                    "Madhya Pradesh","Rajasthan","Uttarakhand","Delhi"),
    (8, 10): _all("Mokshada Ekadashi / Gita Jayanti"),
    (8, 14): _states("Dattatreya Jayanti", "Maharashtra","Karnataka","Goa",
                     "Andhra Pradesh","Telangana","Gujarat"),
    (8, 29): _states("Margashirsha Amavasya", "Maharashtra","Karnataka","Andhra Pradesh"),

    # ════════════════════════════════════════════════════════════════════════
    # PAUSH (9) — December/January
    # ════════════════════════════════════════════════════════════════════════
    (9, 5): _all("Saphala Ekadashi"),
    (9, 10): _all("Paush Putrada Ekadashi"),
    (9, 14): _merge(
        _all("Paush Purnima"),
        _states("Shakambhari Purnima", "Rajasthan","Uttar Pradesh","Madhya Pradesh"),
        _states("Gangasagar Mela", "West Bengal"),
    ),
    (9, 28): _all("Masik Shivratri"),

    # ════════════════════════════════════════════════════════════════════════
    # MAGHA (10) — January/February
    # ════════════════════════════════════════════════════════════════════════
    (10, 4): _merge(
        _all("Vasant Panchami"),
        _states("Saraswati Puja (State Holiday)", "West Bengal","Odisha","Assam",
                "Bihar","Jharkhand","Tripura"),
        _states("Shri Panchami", "West Bengal","Odisha"),
    ),
    (10, 9): _all("Jaya Ekadashi"),
    (10, 14): _merge(
        _all("Maghi Purnima"),
        _states("Magha Mela (Prayagraj)", "Uttar Pradesh","Uttarakhand"),
        _states("Maghi (State Holiday)", "Punjab","Haryana","Chandigarh"),
        _states("Thaipusam", "Tamil Nadu","Kerala","Puducherry"),
    ),
    (10, 28): _all("Maha Shivratri"),

    # ════════════════════════════════════════════════════════════════════════
    # PHALGUNA (11) — February/March
    # ════════════════════════════════════════════════════════════════════════
    (11, 4): _states("Rang Panchami", "Maharashtra","Madhya Pradesh",
                     "Rajasthan","Gujarat","Chhattisgarh"),
    (11, 9): _all("Amalaki Ekadashi"),
    (11, 13): _merge(
        _all("Holika Dahan"),
        _states("Shimga (Holi eve)", "Maharashtra","Goa"),
    ),
    (11, 14): _merge(
        _all("Holi"),
        _states("Dol Jatra / Dol Purnima", "West Bengal","Odisha","Assam","Tripura"),
        _states("Shigmo", "Goa"),
        _states("Yaosang", "Manipur"),
        _states("Phakuwa", "Assam"),
    ),
    (11, 15): _states("Dhuleti / Rangwali Holi",
                      "Gujarat","Rajasthan","Madhya Pradesh",
                      "Uttar Pradesh","Bihar","Chhattisgarh"),
    (11, 29): _states("Phalguna Amavasya / Shani Amavasya",
                      "Rajasthan","Uttar Pradesh","Madhya Pradesh"),
}

# ── Solar / harvest / state-formation festivals ───────────────────────────────
# Fixed by Gregorian/solar calendar — static is genuinely correct for these.

SOLAR_RULES = {
    (1, 1):   _all("New Year's Day"),
    (1, 14):  _merge(
        _all("Makar Sankranti"),
        _states("Pongal", "Tamil Nadu","Puducherry"),
        _states("Lohri", "Punjab","Haryana","Himachal Pradesh","Delhi","Chandigarh","Jammu & Kashmir"),
        _states("Uttarayan / Kite Festival", "Gujarat","Rajasthan"),
        _states("Magh Bihu / Bhogali Bihu", "Assam"),
        _states("Khichdi Parva", "Uttar Pradesh","Bihar","Jharkhand","Uttarakhand"),
        _states("Makara Vilakku", "Kerala","Lakshadweep"),
        _states("Tusu Puja", "West Bengal","Jharkhand","Odisha"),
    ),
    (1, 15):  _states("Thiruvalluvar Day", "Tamil Nadu","Puducherry"),
    (1, 16):  _states("Mattu Pongal / Uzhavar Thirunal", "Tamil Nadu","Puducherry"),
    (1, 23):  _states("Netaji Subhash Chandra Bose Jayanti", "West Bengal","Odisha","Assam","Tripura"),
    (1, 26):  _all("Republic Day"),
    (2, 19):  _states("Chhatrapati Shivaji Maharaj Jayanti", "Maharashtra","Goa","Dadra & Nagar Haveli"),
    (3, 22):  _states("Bihar Diwas", "Bihar","Jharkhand"),
    (4, 5):   _states("Bahu Beej / Gangaur", "Rajasthan","Madhya Pradesh","Gujarat"),
    (4, 14):  _merge(
        _all("Dr. Ambedkar Jayanti"),
        _states("Baisakhi / Vaisakhi", "Punjab","Haryana","Himachal Pradesh","Delhi","Chandigarh","Uttarakhand"),
        _states("Puthandu / Tamil New Year", "Tamil Nadu","Puducherry"),
        _states("Vishu", "Kerala","Lakshadweep"),
        _states("Bohag Bihu / Rongali Bihu", "Assam"),
        _states("Pohela Boishakh / Bengali New Year", "West Bengal","Tripura","Assam"),
        _states("Himachal Day", "Himachal Pradesh"),
    ),
    (4, 15):  _states("Himachal Pradesh Foundation Day", "Himachal Pradesh"),
    (5, 1):   _merge(
        _all("International Labour Day"),
        _states("Maharashtra Day", "Maharashtra","Goa","Dadra & Nagar Haveli"),
        _states("Gujarat Day", "Gujarat"),
    ),
    (5, 16):  _states("Sikkim Statehood Day", "Sikkim"),
    (6, 1):   _states("Telangana Formation Day", "Telangana"),
    (7, 17):  _states("Kharchi Puja", "Tripura"),
    (8, 15):  _all("Independence Day"),
    (8, 26):  _states("Ker Puja", "Tripura"),
    (9, 5):   _all("Teachers Day"),
    (10, 2):  _all("Gandhi Jayanti"),
    (10, 24): _states("Jammu & Kashmir Accession Day", "Jammu & Kashmir","Ladakh"),
    (11, 1):  _merge(
        _states("Karnataka Rajyotsava", "Karnataka"),
        _states("Haryana Day", "Haryana","Chandigarh"),
        _states("Punjab Day", "Punjab","Chandigarh"),
        _states("MP Foundation Day", "Madhya Pradesh","Chhattisgarh"),
        _states("Kerala Piravi", "Kerala","Lakshadweep"),
    ),
    (11, 9):  _states("Uttarakhand Foundation Day", "Uttarakhand"),
    (11, 15): _merge(
        _states("Jharkhand Foundation Day", "Jharkhand"),
        _states("Birsa Munda Jayanti", "Jharkhand","Odisha","West Bengal","Chhattisgarh"),
    ),
    (11, 19): _states("Hornbill Festival begins", "Nagaland"),
    (12, 1):  _states("Nagaland Statehood Day", "Nagaland"),
    (12, 2):  _states("Mizoram Statehood Day", "Mizoram"),
    (12, 19): _states("Goa Liberation Day", "Goa","Dadra & Nagar Haveli"),
    (12, 25): _all("Christmas"),
}

# ── Tribal / regional festivals (fixed by their own solar/harvest calendar) ───

TRIBAL_SOLAR_RULES = {
    # Arunachal Pradesh tribal festivals (approximate Gregorian dates)
    (1, 5):   _states("Losar (Monpa New Year)", "Arunachal Pradesh","Sikkim","Ladakh"),
    (2, 5):   _states("Nyokum Yullo (Nishi tribe)", "Arunachal Pradesh"),
    (3, 5):   _states("Mopin (Adi tribe)", "Arunachal Pradesh"),
    (4, 1):   _states("Ali-Aye Ligang (Mishing tribe)", "Arunachal Pradesh","Assam"),
    (7, 4):   _states("Dree Festival (Apatani tribe)", "Arunachal Pradesh"),
    (9, 1):   _states("Solung (Adi tribe)", "Arunachal Pradesh"),
    # Assam
    (1, 31):  _states("Me-Dam-Me-Phi (Ahom)", "Assam"),
    (4, 13):  _states("Bohag Bihu / Rongali Bihu (State Holiday)", "Assam"),
    (10, 18): _states("Kati Bihu / Kongali Bihu", "Assam"),
    # Meghalaya
    (11, 15): _states("Ka Pomblang Nongkrem (Khasi)", "Meghalaya"),
    (11, 20): _states("Wangala (Garo harvest festival)", "Meghalaya"),
    # Nagaland
    (5, 1):   _states("Moatsu Festival (Ao Naga)", "Nagaland"),
    (12, 1):  _states("Hornbill Festival (State Holiday)", "Nagaland"),
    # Manipur
    (11, 1):  _states("Chavang Kut (Kuki-Zo)", "Manipur"),
    # Mizoram
    (3, 1):   _states("Chapchar Kut (Mizo)", "Mizoram"),
    (9, 20):  _states("Mim Kut (Mizo)", "Mizoram"),
    (12, 31): _states("Pawl Kut (Mizo)", "Mizoram"),
    # Sikkim
    (5, 9):   _states("Saga Dawa (Buddha Purnima - Sikkim)", "Sikkim"),
    (9, 22):  _states("Pang Lhabsol", "Sikkim"),
    (12, 27): _states("Losoong / Namsoong (Sikkimese New Year)", "Sikkim"),
    # Rajasthan
    (3, 18):  _states("Gangaur Festival", "Rajasthan","Madhya Pradesh","Gujarat"),
    (2, 1):   _states("Bikaner Camel Festival", "Rajasthan"),
    (10, 15): _states("Pushkar Camel Fair begins", "Rajasthan"),
    # Odisha
    (8, 20):  _states("Nuakhai (harvest festival)", "Odisha","Chhattisgarh"),
    # Kerala
    (8, 29):  _states("Onam (State Holiday - Thiruvonam)", "Kerala","Lakshadweep"),
    (4, 10):  _states("Thrissur Pooram", "Kerala"),
    # Tamil Nadu
    (1, 13):  _states("Bhogi Pongal", "Tamil Nadu","Puducherry","Andhra Pradesh","Telangana"),
    (1, 17):  _states("Kannum Pongal", "Tamil Nadu","Puducherry"),
    (1, 18):  _states("Jallikattu (Alanganallur)", "Tamil Nadu"),
    # Gujarat
    (3, 28):  _states("Chitra Vichitra Fair", "Gujarat"),
    (9, 10):  _states("Tarnetar Fair", "Gujarat"),
    # Himachal Pradesh
    (10, 2):  _states("Kullu Dussehra begins", "Himachal Pradesh"),
    # Uttarakhand
    (1, 14):  _states("Uttarayani Mela (Bageshwar)", "Uttarakhand"),
    # West Bengal
    (4, 15):  _states("Pohela Boishakh (State Holiday)", "West Bengal","Tripura"),
    (5, 9):   _states("Rabindra Jayanti", "West Bengal","Tripura","Assam"),
    # Goa
    (2, 20):  _states("Goa Carnival", "Goa"),
    (6, 24):  _states("Sao Joao (Feast of St John)", "Goa"),
    (12, 3):  _states("Feast of St Francis Xavier", "Goa"),
    (12, 8):  _states("Feast of Immaculate Conception", "Goa"),
}

# ── Astronomy engine ──────────────────────────────────────────────────────────

def _get_ayanamsa(jd: float) -> float:
    """Lahiri ayanamsa — accurate within ~1 arcminute for modern dates."""
    T = (jd - 2451545.0) / 36525.0
    return 23.85 + 50.3 * T / 3600.0


def _compute_panchang(year: int, month: int, day: int) -> dict:
    """
    Compute all 5 angas of Panchang at IST sunrise (UTC 00:30).
    Returns dict with tithi_index, nakshatra_index, yoga_index,
    karana_index, vara_index, lunar_month_index.
    """
    ephem_date = ephem.Date(f"{year}/{month}/{day} 00:30:00")
    sun  = ephem.Sun(ephem_date)
    moon = ephem.Moon(ephem_date)

    sun_ecl  = math.degrees(ephem.Ecliptic(sun,  epoch=ephem_date).lon)
    moon_ecl = math.degrees(ephem.Ecliptic(moon, epoch=ephem_date).lon)

    jd   = float(ephem_date) + 2415020.0
    ayan = _get_ayanamsa(jd)

    sun_sid  = (sun_ecl  - ayan) % 360.0
    moon_sid = (moon_ecl - ayan) % 360.0

    # Tithi: every 12° of Moon-Sun elongation
    diff          = (moon_ecl - sun_ecl) % 360.0
    tithi_index   = int(diff / 12.0) % 30

    # Nakshatra: Moon sidereal / 13.333°
    nakshatra_index = int(moon_sid / (360.0 / 27)) % 27

    # Yoga: (Sun_sid + Moon_sid) / 13.333°
    yoga_index = int(((sun_sid + moon_sid) % 360.0) / (360.0 / 27)) % 27

    # Karana: half-tithi (every 6°)
    karana_index = int(diff / 6.0) % 11

    # Vara: weekday (0=Mon ephem, adjust to 0=Sun for Hindu vara)
    from datetime import date as _date
    vara_index = _date(year, month, day).weekday()  # 0=Mon..6=Sun

    # Lunar month = Sun's sidereal zodiac sign
    lunar_month_index = int(sun_sid / 30.0) % 12

    return {
        "tithi_index":        tithi_index,
        "nakshatra_index":    nakshatra_index,
        "yoga_index":         yoga_index,
        "karana_index":       karana_index,
        "vara_index":         vara_index,
        "lunar_month_index":  lunar_month_index,
    }


def _collect_state_festivals(p: dict, d) -> dict:
    """
    Build {state: [festival, ...]} for all states for date d.
    p = panchang dict from _compute_panchang.
    """
    state_map = {s: [] for s in ALL_STATES}

    def _apply(rules_dict, key):
        entry = rules_dict.get(key)
        if not entry:
            return
        for state, name in entry.items():
            if name and state in state_map and name not in state_map[state]:
                state_map[state].append(name)

    # 1. Lunar festivals
    _apply(LUNAR_RULES, (p["lunar_month_index"], p["tithi_index"]))

    # 2. Solar festivals
    _apply(SOLAR_RULES, (d.month, d.day))

    # 3. Tribal/regional solar festivals
    _apply(TRIBAL_SOLAR_RULES, (d.month, d.day))

    # 4. Gazetted national holidays (all states)
    india_hols = holidays_lib.India(years=d.year)
    official   = india_hols.get(d)
    if official:
        for s in ALL_STATES:
            if official not in state_map[s]:
                state_map[s].append(official)

    return state_map


# ── Public API ────────────────────────────────────────────────────────────────

def get_calendar_data(date_str: str, state: str = None) -> dict:
    """
    Returns full Kalnirnay-style Panchang + state-wise festivals.
    date_str: YYYY-MM-DD
    state: optional filter (e.g. "Maharashtra")
    """
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    p = _compute_panchang(d.year, d.month, d.day)

    tithi_name       = f"{PAKSHA[p['tithi_index']]} {TITHI_NAMES[p['tithi_index']]}"
    nakshatra_name   = NAKSHATRAS[p["nakshatra_index"]]
    yoga_name        = YOGA_NAMES[p["yoga_index"]]
    karana_name      = KARANA_NAMES[p["karana_index"]]
    vara_name        = VARA_NAMES[p["vara_index"]]
    lunar_month_name = LUNAR_MONTH_NAMES[p["lunar_month_index"]]

    state_festivals = _collect_state_festivals(p, d)

    # Filter to one state if requested
    if state:
        matched = next((s for s in ALL_STATES if s.lower() == state.lower()), None)
        if not matched:
            raise ValueError(f"Unknown state: '{state}'. Use GET /states for valid names.")
        state_festivals = {matched: state_festivals[matched]}

    # Active states only (have at least one festival)
    active = {s: v for s, v in state_festivals.items() if v}

    # All unique festivals across all active states
    seen, all_unique = set(), []
    for fests in active.values():
        for f in fests:
            if f not in seen:
                seen.add(f)
                all_unique.append(f)

    return {
        "date":          date_str,
        "panchang": {
            "vara":        vara_name,
            "lunar_month": lunar_month_name,
            "tithi":       tithi_name,
            "nakshatra":   nakshatra_name,
            "yoga":        yoga_name,
            "karana":      karana_name,
        },
        "festivals_today":  all_unique,
        "state_festivals":  active,
        "features": {
            "day_of_week":    p["vara_index"],
            "month":          d.month,
            "is_weekend":     1 if p["vara_index"] >= 5 else 0,
            "is_holiday":     1 if all_unique else 0,
            "festival_count": len(all_unique),
        },
    }
