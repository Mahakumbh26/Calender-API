"""
calendar_engine.py — Kalnirnay-style Panchang engine
Five angas: Tithi, Vara, Nakshatra, Yoga, Karana

Festival logic:
  LUNAR_RULES   → keyed by (lunar_month, tithi), computed dynamically every year
                  These shift every year — Diwali, Holi, Ganesh Chaturthi, Onam etc.
  SOLAR_RULES   → keyed by (month, day), genuinely fixed by solar calendar
                  Sankranti, Pongal, Baisakhi, state formation days etc.
  No duplicate keys — each (month,day) or (lm,tithi) merges ALL states correctly.
"""

from datetime import datetime
import math
import ephem
import holidays as holidays_lib

# ── Panchang tables ───────────────────────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni",
    "Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha",
    "Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana",
    "Dhanishtha","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]
TITHI_NAMES = [
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]
PAKSHA       = ["Shukla"]*15 + ["Krishna"]*15
YOGA_NAMES   = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda",
    "Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata",
    "Harshana","Vajra","Siddhi","Vyatipata","Variyan","Parigha","Shiva",
    "Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"
]
KARANA_NAMES = [
    "Bava","Balava","Kaulava","Taitila","Garaja",
    "Vanija","Vishti","Shakuni","Chatushpada","Naga","Kimstughna"
]
VARA_NAMES        = ["Somavar","Mangalavar","Budhavar","Guruvar","Shukravar","Shanivar","Ravivar"]
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

# ── helpers ───────────────────────────────────────────────────────────────────

def _all(name):
    return {s: name for s in ALL_STATES}

def _s(name, *states):
    return {s: name for s in states}

def _m(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out

# ═════════════════════════════════════════════════════════════════════════════
# LUNAR RULES — dynamic, shifts every year, computed from tithi + lunar month
# Key: (lunar_month_index 0-11, tithi_index 0-29)
# Value: {state: festival_name}
# ═════════════════════════════════════════════════════════════════════════════

LUNAR_RULES = {

    # ── CHAITRA (0) ───────────────────────────────────────────────────────────
    (0, 0): _m(
        _s("Gudi Padwa", "Maharashtra","Goa","Dadra & Nagar Haveli"),
        _s("Ugadi", "Karnataka","Andhra Pradesh","Telangana"),
        _s("Cheti Chand", "Rajasthan","Gujarat","Delhi","Madhya Pradesh","Chandigarh"),
        _s("Navreh", "Jammu & Kashmir","Ladakh"),
        _s("Sajibu Nongma Panba", "Manipur"),
        _s("Chaitra Navratri begins / Ghatasthapana",
           "Uttar Pradesh","Bihar","Jharkhand","Uttarakhand","Himachal Pradesh",
           "Haryana","Punjab","Rajasthan","Madhya Pradesh","Chhattisgarh","Delhi"),
    ),
    (0, 2): _s("Chaitri Gaur begins (married women festival)",
               "Maharashtra","Goa"),
    (0, 5): _s("Yamuna Chhath","Uttar Pradesh","Bihar","Delhi","Uttarakhand"),
    (0, 7): _m(
        _s("Chaitra Ashtami / Annapoorna Ashtami","West Bengal","Odisha","Assam","Tripura"),
        _s("Sheetala Ashtami","Uttar Pradesh","Rajasthan","Haryana","Punjab","Delhi"),
    ),
    (0, 8): _all("Ram Navami"),
    (0, 13): _all("Mahavir Jayanti"),
    (0, 14): _m(
        _all("Hanuman Jayanti"),
        _s("Chaitra Purnima / Panguni Uthiram","Tamil Nadu","Puducherry","Kerala"),
        _s("Baisakhi Purnima","Punjab","Haryana","Chandigarh"),
    ),
    (0, 29): _s("Chaitra Amavasya","Odisha","West Bengal","Assam","Tripura"),

    # ── VAISHAKHA (1) ─────────────────────────────────────────────────────────
    (1, 2): _m(
        _all("Akshaya Tritiya"),
        _s("Parashurama Jayanti","Kerala","Karnataka","Maharashtra","Goa","Andhra Pradesh","Telangana"),
    ),
    (1, 5): _s("Shankaracharya Jayanti","Kerala","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana"),
    (1, 9): _s("Sita Navami","Uttar Pradesh","Bihar","Jharkhand","Madhya Pradesh","Uttarakhand","Rajasthan"),
    (1, 14): _m(
        _all("Buddha Purnima"),
        _s("Narasimha Jayanti","Andhra Pradesh","Telangana","Karnataka","Tamil Nadu"),
        _s("Vaishakha Purnima","Odisha","West Bengal"),
    ),

    # ── JYESHTHA (2) ──────────────────────────────────────────────────────────
    (2, 4): _s("Skanda Sashti","Tamil Nadu","Puducherry","Kerala","Karnataka","Andhra Pradesh","Telangana"),
    (2, 9): _s("Ganga Dussehra","Uttar Pradesh","Uttarakhand","Bihar","Jharkhand","Delhi","Madhya Pradesh","Rajasthan"),
    (2, 10): _m(
        _s("Vat Savitri Puja","Maharashtra","Goa","Gujarat","Bihar","Jharkhand","Uttar Pradesh","Madhya Pradesh","Rajasthan"),
        _s("Nirjala Ekadashi","Uttar Pradesh","Bihar","Rajasthan","Delhi","Uttarakhand"),
    ),
    (2, 14): _s("Vat Purnima","Maharashtra","Gujarat","Goa"),
    (2, 28): _all("Shani Jayanti"),
    (2, 29): _s("Jyeshtha Amavasya","Uttar Pradesh","Bihar","Rajasthan","Madhya Pradesh","Delhi"),

    # ── ASHADHA (3) ───────────────────────────────────────────────────────────
    (3, 1): _m(
        _all("Jagannath Rath Yatra"),
        _s("Rath Yatra (State Holiday)","Odisha"),
    ),
    (3, 4): _s("Skanda Sashti","Tamil Nadu","Puducherry","Andhra Pradesh","Telangana"),
    (3, 10): _m(
        _all("Devshayani Ekadashi"),
        _s("Ashadhi Ekadashi / Wari","Maharashtra","Goa"),
    ),
    (3, 14): _all("Guru Purnima"),
    (3, 29): _s("Ashadha Amavasya","Karnataka","Andhra Pradesh","Telangana","Tamil Nadu","Kerala"),

    # ── SHRAVANA (4) ──────────────────────────────────────────────────────────
    (4, 0): _s("Shravana Somavar (first Monday of Shravana)",
               "Maharashtra","Goa","Uttar Pradesh","Bihar","Uttarakhand","Rajasthan"),
    (4, 3): _s("Hariyali Teej","Rajasthan","Uttar Pradesh","Haryana","Punjab","Delhi",
               "Madhya Pradesh","Bihar","Uttarakhand","Himachal Pradesh","Chandigarh"),
    (4, 4): _all("Nag Panchami"),
    (4, 6): _s("Tulsi Shravana Saptami","Maharashtra","Gujarat"),
    (4, 7): _s("Mangala Gaur (Shravana Tuesday - new brides)","Maharashtra","Goa"),
    (4, 9): _all("Putrada Ekadashi"),
    (4, 12): _s("Onam - Atham (Day 1)","Kerala","Lakshadweep"),
    (4, 13): _s("Onam - Chithira (Day 2)","Kerala","Lakshadweep"),
    (4, 14): _m(
        _all("Raksha Bandhan"),
        _s("Narali Purnima / Coconut Festival","Maharashtra","Goa"),
        _s("Avani Avittam / Upakarma","Tamil Nadu","Kerala","Puducherry"),
        _s("Jhulan Purnima / Jhulana Yatra","West Bengal","Odisha","Assam"),
        _s("Gamha Purnima","Odisha"),
        _s("Shravana Purnima","Uttar Pradesh","Bihar","Uttarakhand","Rajasthan"),
    ),
    (4, 20): _s("Onam - Thiruvonam (Main Day)","Kerala","Lakshadweep"),
    (4, 22): _s("Kajari Teej","Madhya Pradesh","Uttar Pradesh","Bihar","Rajasthan","Chhattisgarh"),
    (4, 23): _all("Krishna Janmashtami"),
    (4, 24): _s("Nandotsav","Uttar Pradesh","Rajasthan","Madhya Pradesh"),
    (4, 29): _s("Bail Pola / Pithori Amavasya","Maharashtra","Chhattisgarh","Madhya Pradesh"),

    # ── BHADRAPADA (5) ────────────────────────────────────────────────────────
    (5, 1): _s("Hartalika Teej","Maharashtra","Goa","Uttar Pradesh","Bihar","Rajasthan","Madhya Pradesh"),
    (5, 3): _m(
        _all("Ganesh Chaturthi"),
        _s("Vinayaka Chaturthi (State Holiday)","Maharashtra","Goa","Karnataka",
           "Andhra Pradesh","Telangana","Tamil Nadu","Puducherry"),
    ),
    (5, 4): _s("Rishi Panchami","Maharashtra","Gujarat","Rajasthan","Uttar Pradesh","Bihar","Madhya Pradesh"),
    (5, 5): _s("Surya Shashti / Skanda Sashti","Tamil Nadu","Puducherry","Karnataka"),
    (5, 7): _all("Radha Ashtami"),
    (5, 8): _s("Mahalakshmi Puja (3-day)","Maharashtra","Goa"),
    (5, 10): _s("Khudurukuni Osha","Odisha"),
    (5, 11): _s("Onam - Thiruvonam (Main Day)","Kerala","Lakshadweep"),
    (5, 12): _s("Onam - Thiruvonam (Main Day)","Kerala","Lakshadweep"),
    (5, 13): _m(
        _all("Anant Chaturdashi"),
        _s("Ganesh Visarjan (State Holiday)","Maharashtra","Goa"),
    ),
    (5, 14): _s("Bhadrapada Purnima","Odisha","West Bengal","Assam","Tripura"),
    (5, 24): _all("Indira Ekadashi"),
    (5, 29): _m(
        _all("Mahalaya Amavasya / Pitru Paksha ends"),
        _s("Mahalaya / Durga Puja begins","West Bengal","Assam","Odisha","Tripura"),
    ),

    # ── ASHWIN (6) ────────────────────────────────────────────────────────────
    (6, 0): _all("Shardiya Navratri begins / Ghatasthapana"),
    (6, 5): _m(
        _s("Saraswati Puja / Saraswati Avahan","West Bengal","Odisha","Assam","Tripura","Bihar","Jharkhand"),
        _s("Ayudha Puja","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala","Puducherry"),
        _s("Lalita Sashti","Maharashtra","Gujarat"),
    ),
    (6, 6): _s("Saraswati Puja (main day)","West Bengal","Odisha","Assam","Tripura"),
    (6, 7): _m(
        _all("Durga Ashtami / Maha Ashtami"),
        _s("Sandhi Puja","West Bengal","Assam","Tripura"),
    ),
    (6, 8): _m(
        _all("Maha Navami"),
        _s("Ayudha Puja (State Holiday)","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala","Puducherry"),
        _s("Navami Homa","West Bengal","Odisha"),
    ),
    (6, 9): _m(
        _all("Dussehra / Vijayadashami"),
        _s("Mysuru Dasara (State Festival)","Karnataka"),
        _s("Kullu Dussehra","Himachal Pradesh"),
        _s("Bastar Dussehra","Chhattisgarh"),
        _s("Durga Puja Dashami / Sindur Khela","West Bengal","Assam","Tripura"),
        _s("Kota Dussehra","Rajasthan"),
    ),
    (6, 10): _all("Papankusha Ekadashi"),
    (6, 14): _m(
        _all("Sharad Purnima / Kojagiri Purnima"),
        _s("Lakshmi Puja","West Bengal","Odisha","Assam","Tripura"),
        _s("Valmiki Jayanti","Punjab","Haryana","Delhi","Uttar Pradesh","Himachal Pradesh","Chandigarh"),
        _s("Kaumudi Mahotsav","Uttar Pradesh","Bihar"),
    ),

    # ── KARTIK (7) ────────────────────────────────────────────────────────────
    (7, 3): _s("Karva Chauth","Rajasthan","Uttar Pradesh","Punjab","Haryana","Delhi",
               "Himachal Pradesh","Madhya Pradesh","Uttarakhand","Bihar","Jammu & Kashmir","Chandigarh"),
    (7, 7): _s("Ahoi Ashtami","Uttar Pradesh","Rajasthan","Haryana","Punjab","Delhi","Madhya Pradesh","Himachal Pradesh"),
    (7, 10): _s("Govatsa Dwadashi / Vasu Baras","Maharashtra","Gujarat","Goa"),
    (7, 12): _m(
        _all("Dhanteras / Dhanvantari Jayanti"),
        _s("Yama Deepam","Tamil Nadu","Andhra Pradesh","Telangana","Karnataka"),
    ),
    (7, 13): _m(
        _all("Narak Chaturdashi / Choti Diwali"),
        _s("Kali Puja","West Bengal","Assam","Odisha","Tripura"),
        _s("Hanuman Puja","Uttar Pradesh","Bihar","Rajasthan"),
    ),
    # Diwali = Kartik Krishna Amavasya (tithi 29) in most years
    # Some years it falls on Chaturdashi (tithi 28) — cover both
    (7, 28): _m(
        _all("Diwali / Lakshmi Puja"),
        _s("Kali Puja (State Holiday)","West Bengal","Assam","Odisha","Tripura"),
        _s("Naraka Chaturdashi (South)","Tamil Nadu","Karnataka","Andhra Pradesh","Telangana","Kerala","Puducherry"),
    ),
    (7, 29): _m(
        _all("Diwali / Lakshmi Puja"),
        _s("Kali Puja (State Holiday)","West Bengal","Assam","Odisha","Tripura"),
        _s("Naraka Chaturdashi (South)","Tamil Nadu","Karnataka","Andhra Pradesh","Telangana","Kerala","Puducherry"),
    ),
    (7, 15): _m(
        _all("Govardhan Puja / Annakut"),
        _s("Padwa / Bali Pratipada","Maharashtra","Goa"),
        _s("Bali Pratipada","Karnataka","Andhra Pradesh","Telangana"),
        _s("Gujarati New Year / Bestu Varas","Gujarat"),
    ),
    (7, 16): _all("Bhai Dooj / Bhau Beej / Yama Dwitiya"),
    (7, 19): _s("Chhath Puja - Nahay Khay","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"),
    (7, 20): _s("Chhath Puja - Kharna","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"),
    (7, 21): _s("Chhath Puja - Sandhya Arghya","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"),
    (7, 22): _s("Chhath Puja - Usha Arghya","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"),
    (7, 25): _m(
        _all("Dev Uthani Ekadashi / Tulsi Vivah"),
        _s("Kartik Ekadashi / Wari","Maharashtra","Goa"),
    ),
    (7, 14): _m(
        _all("Kartik Purnima / Dev Deepawali"),
        _s("Guru Nanak Jayanti","Punjab","Haryana","Delhi","Himachal Pradesh","Uttarakhand","Chandigarh","Jammu & Kashmir"),
        _s("Pushkar Fair","Rajasthan"),
        _s("Tripuri Purnima","Tripura"),
        _s("Dev Deepawali (Varanasi)","Uttar Pradesh","Bihar","Uttarakhand"),
    ),

    # ── MARGASHIRSHA (8) ──────────────────────────────────────────────────────
    (8, 0): _s("Champa Shashthi / Khandoba Festival begins","Maharashtra","Goa"),
    (8, 4): _s("Vivah Panchami","Uttar Pradesh","Bihar","Madhya Pradesh","Rajasthan","Uttarakhand","Delhi"),
    (8, 5): _s("Champa Shashthi / Khandoba Festival (main day)","Maharashtra","Goa"),
    (8, 10): _all("Mokshada Ekadashi / Gita Jayanti"),
    (8, 14): _s("Dattatreya Jayanti","Maharashtra","Karnataka","Goa","Andhra Pradesh","Telangana","Gujarat"),
    (8, 29): _s("Margashirsha Amavasya","Maharashtra","Karnataka","Andhra Pradesh","Telangana"),

    # ── PAUSH (9) ─────────────────────────────────────────────────────────────
    (9, 5): _all("Saphala Ekadashi"),
    (9, 10): _all("Paush Putrada Ekadashi"),
    (9, 14): _m(
        _all("Paush Purnima"),
        _s("Shakambhari Purnima","Rajasthan","Uttar Pradesh","Madhya Pradesh"),
        _s("Gangasagar Mela","West Bengal"),
    ),
    (9, 28): _all("Masik Shivratri"),

    # ── MAGHA (10) ────────────────────────────────────────────────────────────
    (10, 4): _m(
        _all("Vasant Panchami"),
        _s("Saraswati Puja (State Holiday)","West Bengal","Odisha","Assam","Bihar","Jharkhand","Tripura"),
        _s("Shri Panchami","West Bengal","Odisha"),
    ),
    (10, 9): _all("Jaya Ekadashi"),
    (10, 14): _m(
        _all("Maghi Purnima"),
        _s("Magha Mela (Prayagraj)","Uttar Pradesh","Uttarakhand"),
        _s("Maghi (State Holiday)","Punjab","Haryana","Chandigarh"),
        _s("Thaipusam","Tamil Nadu","Kerala","Puducherry"),
    ),
    (10, 28): _all("Maha Shivratri"),

    # ── PHALGUNA (11) ─────────────────────────────────────────────────────────
    (11, 4): _s("Rang Panchami","Maharashtra","Madhya Pradesh","Rajasthan","Gujarat","Chhattisgarh"),
    (11, 9): _all("Amalaki Ekadashi"),
    (11, 13): _m(
        _all("Holika Dahan"),
        _s("Shimga (Holi eve)","Maharashtra","Goa"),
    ),
    (11, 14): _m(
        _all("Holi"),
        _s("Dol Jatra / Dol Purnima","West Bengal","Odisha","Assam","Tripura"),
        _s("Shigmo","Goa"),
        _s("Yaosang","Manipur"),
        _s("Phakuwa","Assam"),
    ),
    (11, 15): _s("Dhuleti / Rangwali Holi","Gujarat","Rajasthan","Madhya Pradesh","Uttar Pradesh","Bihar","Chhattisgarh"),
    (11, 29): _s("Phalguna Amavasya","Rajasthan","Uttar Pradesh","Madhya Pradesh"),
}

# ═════════════════════════════════════════════════════════════════════════════
# SOLAR RULES — fixed by solar/Gregorian calendar, correct to be static
# Key: (month, day)
# Value: {state: festival_name}
# IMPORTANT: No duplicate keys — each date has ONE merged dict for all states
# ═════════════════════════════════════════════════════════════════════════════

def _solar_rules():
    """Build solar rules as a list of (key, state_dict) then merge per key."""
    entries = [

        # ── National ──────────────────────────────────────────────────────────
        ((1,  1),  _all("New Year's Day")),
        ((1, 12),  _s("Swami Vivekananda Jayanti","West Bengal","Assam","Odisha","Tripura","Andaman & Nicobar")),
        ((1, 23),  _s("Netaji Subhash Chandra Bose Jayanti","West Bengal","Odisha","Assam","Tripura")),
        ((1, 26),  _all("Republic Day")),
        ((2, 19),  _s("Chhatrapati Shivaji Maharaj Jayanti","Maharashtra","Goa","Dadra & Nagar Haveli")),
        ((3, 23),  _s("Shaheed Diwas (Bhagat Singh)","Punjab","Haryana","Delhi","Chandigarh","Uttar Pradesh")),
        ((4, 14),  _all("Dr. Ambedkar Jayanti")),
        ((5,  1),  _all("International Labour Day")),
        ((8, 15),  _all("Independence Day")),
        ((9,  5),  _all("Teachers Day")),
        ((10, 2),  _all("Gandhi Jayanti")),
        ((12,25),  _all("Christmas")),

        # ── Makar Sankranti / Jan 14 — solar, genuinely fixed ─────────────────
        ((1, 13),  _s("Bhogi Pongal","Tamil Nadu","Puducherry","Andhra Pradesh","Telangana")),
        ((1, 14),  _m(
            _all("Makar Sankranti"),
            _s("Thai Pongal","Tamil Nadu","Puducherry"),
            _s("Lohri","Punjab","Haryana","Himachal Pradesh","Delhi","Chandigarh","Jammu & Kashmir"),
            _s("Uttarayan / Kite Festival","Gujarat","Rajasthan"),
            _s("Magh Bihu / Bhogali Bihu","Assam"),
            _s("Khichdi Parva","Uttar Pradesh","Bihar","Jharkhand","Uttarakhand"),
            _s("Makara Vilakku (Sabarimala)","Kerala","Lakshadweep"),
            _s("Tusu Puja / Makar Parab","West Bengal","Jharkhand","Odisha"),
            _s("Uttarayani Mela (Bageshwar)","Uttarakhand"),
            _s("Sankranti / Ellu Birodhu","Karnataka"),
            _s("Til-Gul Sankranti","Maharashtra","Goa"),
            _s("Maghi (Muktsar Fair)","Punjab"),
        )),
        ((1, 15),  _m(
            _s("Thiruvalluvar Day","Tamil Nadu","Puducherry"),
            _s("Magh Bihu (State Holiday)","Assam"),
        )),
        ((1, 16),  _s("Mattu Pongal / Uzhavar Thirunal","Tamil Nadu","Puducherry")),
        ((1, 17),  _s("Kannum Pongal","Tamil Nadu","Puducherry")),
        ((1, 18),  _m(
            _s("Jallikattu","Tamil Nadu"),
            _s("Lui-Ngai-Ni (Naga New Year)","Nagaland","Manipur"),
        )),
        ((1, 31),  _s("Me-Dam-Me-Phi (Ahom)","Assam")),

        # ── February ──────────────────────────────────────────────────────────
        ((2,  1),  _s("Surajkund Craft Mela","Haryana","Delhi")),
        ((2, 19),  _s("Shivaji Jayanti (State Holiday)","Maharashtra","Goa")),

        # ── March ─────────────────────────────────────────────────────────────
        ((3,  1),  _s("Chapchar Kut (State Holiday)","Mizoram")),
        ((3, 18),  _s("Gangaur","Rajasthan","Madhya Pradesh","Gujarat")),
        ((3, 22),  _s("Bihar Diwas","Bihar","Jharkhand")),
        ((3, 30),  _s("Rajasthan Day","Rajasthan")),

        # ── April ─────────────────────────────────────────────────────────────
        ((4,  1),  _s("Utkal Diwas (Odisha Foundation Day)","Odisha")),
        ((4, 10),  _s("Thrissur Pooram","Kerala")),
        ((4, 13),  _m(
            _s("Bohag Bihu / Rongali Bihu (State Holiday)","Assam"),
            _s("Sajibu Cheiraoba (Meitei New Year)","Manipur"),
        )),
        ((4, 14),  _m(
            _s("Baisakhi / Vaisakhi","Punjab","Haryana","Himachal Pradesh","Delhi","Chandigarh","Uttarakhand"),
            _s("Puthandu / Tamil New Year","Tamil Nadu","Puducherry"),
            _s("Vishu","Kerala","Lakshadweep"),
            _s("Pohela Boishakh / Bengali New Year","West Bengal","Tripura","Assam"),
            _s("Himachal Day","Himachal Pradesh"),
            _s("Pana Sankranti / Maha Vishuba Sankranti","Odisha"),
            _s("Baisakhi (State Holiday)","Punjab","Haryana"),
        )),
        ((4, 15),  _m(
            _s("Himachal Pradesh Foundation Day","Himachal Pradesh"),
            _s("Pohela Boishakh (State Holiday)","West Bengal","Tripura"),
        )),

        # ── May ───────────────────────────────────────────────────────────────
        ((5,  1),  _m(
            _s("Maharashtra Day","Maharashtra","Goa","Dadra & Nagar Haveli"),
            _s("Gujarat Day","Gujarat"),
        )),
        ((5,  9),  _s("Rabindra Jayanti","West Bengal","Tripura","Assam")),
        ((5, 16),  _s("Sikkim Statehood Day","Sikkim")),

        # ── June ──────────────────────────────────────────────────────────────
        ((6,  1),  _s("Telangana Formation Day","Telangana")),
        ((6, 13),  _s("Feast of St Anthony","Goa")),
        ((6, 20),  _m(
            _s("Ambubachi Mela (Kamakhya)","Assam"),
            _s("Raja Parba","Odisha"),
        )),
        ((6, 24),  _s("Sao Joao","Goa")),

        # ── July ──────────────────────────────────────────────────────────────
        ((7,  1),  _s("Tuluni Festival (Sumi Naga)","Nagaland")),
        ((7, 17),  _s("Kharchi Puja (State Holiday)","Tripura")),

        # ── August ────────────────────────────────────────────────────────────
        ((8,  9),  _s("Karma Puja","Jharkhand","Odisha","Chhattisgarh","West Bengal")),
        ((8, 15),  _s("Feast of Assumption of Our Lady","Goa")),
        ((8, 20),  _s("Nuakhai (State Holiday)","Odisha","Chhattisgarh")),
        ((8, 26),  _s("Ker Puja","Tripura")),

        # ── September ─────────────────────────────────────────────────────────
        ((9,  1),  _m(
            _s("Bathukamma begins","Telangana"),
            _s("Sree Narayana Guru Samadhi","Kerala"),
            _s("Ladakh Festival","Ladakh"),
        )),
        ((9, 18),  _s("Pola / Bail Pola","Maharashtra","Chhattisgarh","Madhya Pradesh")),
        ((9, 20),  _s("Mim Kut","Mizoram")),
        ((9, 22),  _s("Pang Lhabsol","Sikkim")),

        # ── October ───────────────────────────────────────────────────────────
        ((10, 2),  _m(
            _s("Bathukamma (main day)","Telangana"),
            _s("Kullu Dussehra begins","Himachal Pradesh"),
        )),
        ((10, 15), _s("Pushkar Camel Fair","Rajasthan")),
        ((10, 18), _s("Kongali Bihu / Kati Bihu","Assam")),
        ((10, 20), _s("Marwar Festival (Jodhpur)","Rajasthan")),
        ((10, 24), _s("J&K Accession Day","Jammu & Kashmir","Ladakh")),

        # ── November ──────────────────────────────────────────────────────────
        ((11, 1),  _m(
            _s("Karnataka Rajyotsava (State Holiday)","Karnataka"),
            _s("Haryana Day","Haryana","Chandigarh"),
            _s("Punjab Day","Punjab","Chandigarh"),
            _s("MP Foundation Day","Madhya Pradesh","Chhattisgarh"),
            _s("Kerala Piravi","Kerala","Lakshadweep"),
            _s("Chavang Kut (Kuki-Zo)","Manipur"),
        )),
        ((11, 9),  _s("Uttarakhand Foundation Day","Uttarakhand")),
        ((11, 15), _m(
            _s("Jharkhand Foundation Day","Jharkhand"),
            _s("Birsa Munda Jayanti","Jharkhand","Odisha","West Bengal","Chhattisgarh"),
            _s("Nongkrem Dance Festival (Khasi)","Meghalaya"),
        )),
        ((11, 19), _s("Hornbill Festival begins","Nagaland")),
        ((11, 20), _s("Wangala (100 Drums - Garo)","Meghalaya")),
        ((11, 28), _s("Ningol Chakouba","Manipur")),

        # ── December ──────────────────────────────────────────────────────────
        ((12, 1),  _m(
            _s("Nagaland Statehood Day / Hornbill Festival","Nagaland"),
            _s("International Sand Art Festival (Puri)","Odisha"),
        )),
        ((12, 2),  _s("Mizoram Statehood Day","Mizoram")),
        ((12, 3),  _s("Feast of St Francis Xavier","Goa")),
        ((12, 8),  _s("Feast of Immaculate Conception","Goa")),
        ((12, 19), _s("Goa Liberation Day","Goa","Dadra & Nagar Haveli")),
        ((12, 27), _s("Losoong / Namsoong (Sikkimese New Year)","Sikkim")),
        ((12, 31), _s("Pawl Kut","Mizoram")),

        # ── Maharashtra deep local ─────────────────────────────────────────────
        ((1,  6),  _s("Feast of Three Kings (Goa/MH Christians)","Goa","Maharashtra")),
        ((2, 20),  _s("Goa Carnival","Goa")),

        # ── Karnataka deep local ───────────────────────────────────────────────
        ((1, 14),  _s("Sankranti / Ellu Birodhu (Karnataka)","Karnataka")),  # already merged above

        # ── Kerala deep local ─────────────────────────────────────────────────
        ((2, 15),  _s("Attukal Pongala (Thiruvananthapuram)","Kerala")),
        ((4, 10),  _s("Thrissur Pooram (State Festival)","Kerala")),
        ((8, 29),  _s("Onam / Thiruvonam (State Holiday)","Kerala","Lakshadweep")),
        ((11, 5),  _s("Aranmula Boat Race","Kerala")),
        ((8, 10),  _s("Nehru Trophy Boat Race (Alappuzha)","Kerala")),

        # ── Arunachal Pradesh tribal ───────────────────────────────────────────
        ((1,  5),  _s("Losar (Monpa New Year)","Arunachal Pradesh","Sikkim","Ladakh")),
        ((2, 26),  _s("Nyokum Yullo (Nishi tribe)","Arunachal Pradesh")),
        ((4,  5),  _s("Mopin (Adi tribe)","Arunachal Pradesh")),
        ((4,  1),  _s("Ali-Aye Ligang (Mishing tribe)","Arunachal Pradesh","Assam")),
        ((7,  5),  _s("Dree Festival (Apatani tribe)","Arunachal Pradesh")),
        ((9,  5),  _s("Solung (Adi tribe)","Arunachal Pradesh")),
        ((10,20),  _s("Boori Boot (Nyishi tribe)","Arunachal Pradesh")),
        ((12,10),  _s("Oriah (Wancho tribe)","Arunachal Pradesh")),

        # ── Nagaland tribal ───────────────────────────────────────────────────
        ((5,  1),  _s("Moatsu (Ao Naga)","Nagaland")),
        ((8, 10),  _s("Sekrenyi (Angami Naga)","Nagaland")),

        # ── Sikkim ────────────────────────────────────────────────────────────
        ((5, 16),  _s("Sikkim Statehood Day (State Holiday)","Sikkim")),
        ((5, 23),  _s("Saga Dawa","Sikkim")),

        # ── Odisha ────────────────────────────────────────────────────────────
        ((5,  1),  _s("Chandan Yatra begins","Odisha")),
        ((10, 1),  _s("Konark Dance Festival","Odisha")),

        # ── Rajasthan ─────────────────────────────────────────────────────────
        ((2,  1),  _s("Bikaner Camel Festival","Rajasthan")),

        # ── Uttarakhand ───────────────────────────────────────────────────────
        ((3, 22),  _s("Phool Dei (Spring Festival)","Uttarakhand")),
        ((7, 15),  _s("Harela (Kumaon harvest)","Uttarakhand")),

        # ── Jammu & Kashmir ───────────────────────────────────────────────────
        ((6, 15),  _s("Hemis Festival","Ladakh","Jammu & Kashmir")),

        # ── Puducherry ────────────────────────────────────────────────────────
        ((8, 15),  _s("Puducherry De Facto Transfer Day","Puducherry")),
        ((11, 1),  _s("Puducherry Liberation Day","Puducherry")),

        # ── Andaman & Nicobar ─────────────────────────────────────────────────
        ((3,  4),  _s("Island Tourism Festival","Andaman & Nicobar")),
    ]

    # Merge all entries with same key into one dict
    result = {}
    for key, state_dict in entries:
        if key not in result:
            result[key] = {}
        result[key].update(state_dict)
    return result

SOLAR_RULES = _solar_rules()


# ═════════════════════════════════════════════════════════════════════════════
# ASTRONOMY ENGINE
# ═════════════════════════════════════════════════════════════════════════════

def _get_ayanamsa(jd: float) -> float:
    T = (jd - 2451545.0) / 36525.0
    return 23.85 + 50.3 * T / 3600.0


def _compute_panchang(year: int, month: int, day: int) -> dict:
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
    yoga_index      = int(((sun_sid + moon_sid) % 360.0) / (360.0 / 27)) % 27
    karana_index    = int(diff / 6.0) % 11
    # Lunar month = Sun's sidereal zodiac sign (Saura month — used by Kalnirnay)
    # Aries=Chaitra(0), Taurus=Vaishakha(1), ... Pisces=Phalguna(11)
    # NOTE: Sun's sign lags traditional lunar month name by 1.
    # We apply +1 shift here so LUNAR_RULES keys match traditional names.
    lunar_month_index = (int(sun_sid / 30.0) + 1) % 12

    from datetime import date as _date
    vara_index = _date(year, month, day).weekday()

    return {
        "tithi_index": tithi_index, "nakshatra_index": nakshatra_index,
        "yoga_index": yoga_index, "karana_index": karana_index,
        "vara_index": vara_index, "lunar_month_index": lunar_month_index,
    }


def _find_last_new_moon(ephem_date) -> ephem.Date:
    return ephem.previous_new_moon(ephem_date)


def _collect_state_festivals(p: dict, d) -> dict:
    state_map = {s: [] for s in ALL_STATES}

    def _apply(rule_dict, key):
        entry = rule_dict.get(key)
        if not entry:
            return
        for state, name in entry.items():
            if name and state in state_map and name not in state_map[state]:
                state_map[state].append(name)

    _apply(LUNAR_RULES, (p["lunar_month_index"], p["tithi_index"]))

    # Nakshatra-based festivals (Onam Thiruvonam = Shravana nakshatra in Bhadrapada)
    if p["lunar_month_index"] == 5 and p["nakshatra_index"] == 21:
        for s in ["Kerala", "Lakshadweep"]:
            if "Onam - Thiruvonam (Main Day)" not in state_map[s]:
                state_map[s].append("Onam - Thiruvonam (Main Day)")

    _apply(SOLAR_RULES, (d.month, d.day))

    india_hols = holidays_lib.India(years=d.year)
    official   = india_hols.get(d)
    if official:
        for s in ALL_STATES:
            if official not in state_map[s]:
                state_map[s].append(official)

    return state_map


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

def get_calendar_data(date_str: str, state: str = None) -> dict:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    p = _compute_panchang(d.year, d.month, d.day)

    state_festivals = _collect_state_festivals(p, d)

    if state:
        matched = next((s for s in ALL_STATES if s.lower() == state.lower()), None)
        if not matched:
            raise ValueError(f"Unknown state: '{state}'. Use GET /states for valid names.")
        state_festivals = {matched: state_festivals[matched]}

    active = {s: v for s, v in state_festivals.items() if v}

    seen, all_unique = set(), []
    for fests in active.values():
        for f in fests:
            if f not in seen:
                seen.add(f)
                all_unique.append(f)

    return {
        "date": date_str,
        "panchang": {
            "vara":        VARA_NAMES[p["vara_index"]],
            "lunar_month": LUNAR_MONTH_NAMES[p["lunar_month_index"]],
            "tithi":       f"{PAKSHA[p['tithi_index']]} {TITHI_NAMES[p['tithi_index']]}",
            "nakshatra":   NAKSHATRAS[p["nakshatra_index"]],
            "yoga":        YOGA_NAMES[p["yoga_index"]],
            "karana":      KARANA_NAMES[p["karana_index"]],
        },
        "festivals_today": all_unique,
        "state_festivals":  active,
        "features": {
            "day_of_week":    p["vara_index"],
            "month":          d.month,
            "is_weekend":     1 if p["vara_index"] >= 5 else 0,
            "is_holiday":     1 if all_unique else 0,
            "festival_count": len(all_unique),
        },
    }
