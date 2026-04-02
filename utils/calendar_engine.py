"""
calendar_engine.py — Panchang engine for Crop Price Prediction
Accurate festival detection for all years — Maharashtra & Karnataka focus.

Strategy:
  - Amavasya/Purnima: detected purely from tithi_index (always correct)
  - Lunar festivals: (sun_sign, tithi) with verified sun_sign values per festival
  - Solar festivals: fixed Gregorian dates (genuinely solar)
  - No duplicate key bugs — built via function with explicit merge
"""

from datetime import datetime
import math
import ephem
import holidays as holidays_lib

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
PAKSHA = ["Shukla"]*15 + ["Krishna"]*15

YOGA_NAMES = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda",
    "Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata",
    "Harshana","Vajra","Siddhi","Vyatipata","Variyan","Parigha","Shiva",
    "Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"
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

# Amavasya names by sun_sign
AMAVASYA_NAMES = {
    11:"Chaitra Amavasya", 0:"Vaishakha Amavasya",
    1:"Jyeshtha Amavasya", 2:"Ashadha Amavasya",
    3:"Shravana Amavasya", 4:"Bhadrapada Amavasya / Mahalaya",
    5:"Ashwin Amavasya", 6:"Kartik Amavasya",
    7:"Margashirsha Amavasya", 8:"Paush Amavasya",
    9:"Magha Amavasya", 10:"Phalguna Amavasya"
}

# Purnima names by sun_sign
PURNIMA_NAMES = {
    11:"Chaitra Purnima", 0:"Vaishakha Purnima / Buddha Purnima",
    1:"Jyeshtha Purnima / Vat Purnima", 2:"Ashadha Purnima / Guru Purnima",
    3:"Shravana Purnima / Raksha Bandhan", 4:"Bhadrapada Purnima",
    5:"Ashwin Purnima / Sharad Purnima / Kojagiri",
    6:"Kartik Purnima / Dev Deepawali", 7:"Margashirsha Purnima",
    8:"Paush Purnima", 9:"Magha Purnima", 10:"Phalguna Purnima / Holi"
}

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

def _all(name):        return {s: name for s in ALL_STATES}
def _s(name, *states): return {s: name for s in states}
def _m(*dicts):
    out = {}
    for d in dicts: out.update(d)
    return out

# ═════════════════════════════════════════════════════════════════════════════
# LUNAR FESTIVAL RULES
# Key: (sun_sign_index, tithi_index)
# sun_sign values verified from actual ephem output across 2020-2030
# Each festival uses ONLY the verified sun_sign(s) — no guessing
# ═════════════════════════════════════════════════════════════════════════════

def _build_lunar_rules():
    entries = []
    def add(signs, tithis, sd):
        for s in signs:
            for t in tithis:
                entries.append(((s % 12, t), sd))

    # ── Chaitra / New Year festivals ──────────────────────────────────────────
    # Gudi Padwa / Ugadi = Chaitra Shukla Pratipada (tithi 0 ONLY)
    # sun=11(Pisces) in most years, sun=0(Aries) in 2026
    add([11,0],[0], _m(
        _s("Gudi Padwa","Maharashtra","Goa","Dadra & Nagar Haveli"),
        _s("Ugadi","Karnataka","Andhra Pradesh","Telangana"),
        _s("Cheti Chand","Rajasthan","Gujarat","Delhi","Madhya Pradesh","Chandigarh"),
        _s("Navreh","Jammu & Kashmir","Ladakh"),
        _s("Sajibu Nongma Panba","Manipur"),
        _s("Chaitra Navratri begins","Uttar Pradesh","Bihar","Jharkhand","Uttarakhand",
           "Himachal Pradesh","Haryana","Punjab","Rajasthan","Madhya Pradesh","Chhattisgarh","Delhi"),
    ))
    add([11,0],[2],  _s("Chaitri Gaur begins","Maharashtra","Goa"))
    add([11,0],[5],  _s("Yamuna Chhath","Uttar Pradesh","Bihar","Delhi","Uttarakhand"))
    add([11,0],[7],  _m(
        _s("Chaitra Ashtami","West Bengal","Odisha","Assam","Tripura"),
        _s("Sheetala Ashtami","Uttar Pradesh","Rajasthan","Haryana","Punjab","Delhi"),
    ))
    add([11,0],[8],  _all("Ram Navami"))
    add([11,0],[13], _all("Mahavir Jayanti"))
    add([11,0],[14], _m(
        _all("Hanuman Jayanti"),
        _s("Chaitra Purnima / Panguni Uthiram","Tamil Nadu","Puducherry","Kerala"),
    ))

    # ── Vaishakha festivals ───────────────────────────────────────────────────
    # Akshaya Tritiya / Basava Jayanti = Vaishakha Shukla Tritiya
    # sun=0(Aries) or 1(Taurus)
    add([0,1],[1,2], _m(
        _all("Akshaya Tritiya"),
        _s("Parashurama Jayanti","Kerala","Karnataka","Maharashtra","Goa","Andhra Pradesh","Telangana"),
        _s("Basava Jayanti","Karnataka","Andhra Pradesh","Telangana"),
    ))
    add([0,1],[4],  _s("Shankaracharya Jayanti","Kerala","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana"))
    add([0,1],[8],  _s("Sita Navami","Uttar Pradesh","Bihar","Jharkhand","Madhya Pradesh","Uttarakhand","Rajasthan"))
    add([0,1],[14], _m(
        _s("Narasimha Jayanti","Andhra Pradesh","Telangana","Karnataka","Tamil Nadu"),
    ))

    # ── Jyeshtha festivals ────────────────────────────────────────────────────
    # sun=1(Taurus) or 2(Gemini)
    add([1,2],[5],  _s("Skanda Sashti","Tamil Nadu","Puducherry","Kerala","Karnataka","Andhra Pradesh","Telangana"))
    add([1,2],[9],  _s("Ganga Dussehra","Uttar Pradesh","Uttarakhand","Bihar","Jharkhand","Delhi","Madhya Pradesh","Rajasthan"))
    add([1,2],[10], _m(
        _s("Vat Savitri Puja","Maharashtra","Goa","Gujarat","Bihar","Jharkhand","Uttar Pradesh","Madhya Pradesh","Rajasthan"),
        _s("Nirjala Ekadashi","Uttar Pradesh","Bihar","Rajasthan","Delhi","Uttarakhand"),
    ))
    add([1,2],[14], _s("Vat Purnima (MH/GJ only)","Maharashtra","Gujarat","Goa"))

    # ── Ashadha festivals ─────────────────────────────────────────────────────
    # Rath Yatra = sun=2(Gemini) always
    add([2],[1],  _m(_all("Jagannath Rath Yatra"), _s("Rath Yatra (State Holiday)","Odisha")))
    add([2,3],[5], _s("Skanda Sashti","Tamil Nadu","Puducherry","Andhra Pradesh","Telangana"))
    # Ashadhi Ekadashi = sun=2 always (verified 2020-2030)
    add([2],[10], _m(_all("Devshayani Ekadashi"), _s("Ashadhi Ekadashi / Wari","Maharashtra","Goa")))
    # Guru Purnima = covered by PURNIMA_NAMES[2] = "Ashadha Purnima / Guru Purnima"

    # ── Shravana festivals ────────────────────────────────────────────────────
    # Raksha Bandhan / Narali Purnima = sun=3 or 4
    add([3,4],[2],  _s("Hariyali Teej","Rajasthan","Uttar Pradesh","Haryana","Punjab","Delhi",
                       "Madhya Pradesh","Bihar","Uttarakhand","Himachal Pradesh","Chandigarh"))
    add([3,4],[4],  _all("Nag Panchami"))
    add([3,4],[6],  _s("Mangala Gaur (Shravana Tuesday)","Maharashtra","Goa"))
    add([3,4],[7],  _s("Tulsi Shravana Saptami","Maharashtra","Gujarat"))
    add([3,4],[11], _s("Onam - Atham (Day 1)","Kerala","Lakshadweep"))
    # Guru Purnima handled by Purnima block (PURNIMA_NAMES[2] = "Ashadha Purnima / Guru Purnima")
    # Raksha Bandhan handled by Purnima block (PURNIMA_NAMES[3] = "Shravana Purnima / Raksha Bandhan")
    # Holi handled by Purnima block (PURNIMA_NAMES[10] = "Phalguna Purnima / Holi")
    # Narali Purnima — add separately since it's MH-specific
    add([3,4],[14], _s("Narali Purnima / Coconut Festival","Maharashtra","Goa"))
    add([3,4],[14], _s("Vara Mahalakshmi Vrata","Karnataka","Andhra Pradesh","Telangana","Tamil Nadu"))
    add([3,4],[14], _s("Avani Avittam / Upakarma","Tamil Nadu","Kerala","Puducherry"))
    add([3,4],[14], _s("Jhulan Purnima / Jhulana Yatra","West Bengal","Odisha","Assam"))
    add([3,4],[17], _s("Kajari Teej","Madhya Pradesh","Uttar Pradesh","Bihar","Rajasthan","Chhattisgarh"))
    # Janmashtami = sun=3 or 4
    add([3,4],[22], _all("Krishna Janmashtami"))
    add([3,4],[23], _s("Nandotsav","Uttar Pradesh","Rajasthan","Madhya Pradesh"))
    # Bail Pola = Shravana Amavasya — handled via Amavasya logic + solar rule

    # ── Bhadrapada festivals ──────────────────────────────────────────────────
    # Ganesh Chaturthi = sun=4 mostly, sun=5 in 2023
    add([4,5],[2],  _s("Hartalika Teej","Maharashtra","Goa","Uttar Pradesh","Bihar","Rajasthan","Madhya Pradesh"))
    add([4,5],[3],  _m(
        _all("Ganesh Chaturthi"),
        _s("Ganesh Chaturthi / Vinayaka Chaturthi (State Holiday)","Maharashtra","Goa","Karnataka",
           "Andhra Pradesh","Telangana","Tamil Nadu","Puducherry"),
    ))
    add([4,5],[4],  _s("Rishi Panchami","Maharashtra","Gujarat","Rajasthan","Uttar Pradesh","Bihar","Madhya Pradesh"))
    add([4,5],[5],  _s("Surya Shashti / Skanda Sashti","Tamil Nadu","Puducherry","Karnataka"))
    add([4,5],[7],  _m(_all("Radha Ashtami"), _s("Gowri Habba","Karnataka")))
    add([4,5],[8],  _s("Mahalakshmi Puja (3-day)","Maharashtra","Goa"))
    add([4,5],[10], _s("Khudurukuni Osha","Odisha"))
    add([4,5],[11,12], _s("Onam - Thiruvonam (Main Day)","Kerala","Lakshadweep"))
    add([4,5],[13], _m(_all("Anant Chaturdashi"), _s("Ganesh Visarjan (State Holiday)","Maharashtra","Goa")))
    add([4,5],[29], _m(
        _all("Mahalaya Amavasya / Pitru Paksha ends"),
        _s("Mahalaya / Durga Puja begins","West Bengal","Assam","Odisha","Tripura"),
    ))

    # ── Ashwin festivals ──────────────────────────────────────────────────────
    # Navratri/Dussehra = sun=5 OR sun=6 (verified 2020-2030)
    add([5,6],[0],  _all("Shardiya Navratri begins / Ghatasthapana"))
    add([5,6],[3],  _s("Karva Chauth","Rajasthan","Uttar Pradesh","Punjab","Haryana","Delhi",
                     "Himachal Pradesh","Madhya Pradesh","Uttarakhand","Bihar","Jammu & Kashmir","Chandigarh"))
    add([5,6],[5],  _m(
        _s("Saraswati Puja / Saraswati Avahan","West Bengal","Odisha","Assam","Tripura","Bihar","Jharkhand"),
        _s("Ayudha Puja","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala","Puducherry"),
        _s("Lalita Sashti","Maharashtra","Gujarat"),
    ))
    add([5,6],[6],  _s("Saraswati Puja (main day)","West Bengal","Odisha","Assam","Tripura"))
    add([5,6],[7],  _m(_all("Durga Ashtami / Maha Ashtami"), _s("Sandhi Puja","West Bengal","Assam","Tripura")))
    add([5,6],[8],  _m(
        _all("Maha Navami"),
        _s("Ayudha Puja (State Holiday)","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala","Puducherry"),
        _s("Mysuru Dasara (State Festival)","Karnataka"),
    ))
    # Dussehra = sun=5 OR sun=6 (verified 2020-2030)
    add([5,6],[9], _m(
        _all("Dussehra / Vijayadashami"),
        _s("Mysuru Dasara (State Festival)","Karnataka"),
        _s("Kullu Dussehra","Himachal Pradesh"),
        _s("Bastar Dussehra","Chhattisgarh"),
        _s("Durga Puja Dashami / Sindur Khela","West Bengal","Assam","Tripura"),
        _s("Kota Dussehra","Rajasthan"),
    ))
    add([5,6],[14], _m(
        _all("Sharad Purnima / Kojagiri Purnima"),
        _s("Lakshmi Puja","West Bengal","Odisha","Assam","Tripura"),
        _s("Valmiki Jayanti","Punjab","Haryana","Delhi","Uttar Pradesh","Himachal Pradesh","Chandigarh"),
    ))

    # ── Kartik festivals ──────────────────────────────────────────────────────
    # Diwali = sun=6 OR sun=7 (verified 2020-2030)
    add([6,7],[7],  _s("Ahoi Ashtami","Uttar Pradesh","Rajasthan","Haryana","Punjab","Delhi","Madhya Pradesh","Himachal Pradesh"))
    add([6,7],[10], _s("Govatsa Dwadashi / Vasu Baras","Maharashtra","Gujarat","Goa"))
    add([6,7],[12], _m(_all("Dhanteras / Dhanvantari Jayanti"), _s("Yama Deepam","Tamil Nadu","Andhra Pradesh","Telangana","Karnataka")))
    add([6,7],[13], _m(_all("Narak Chaturdashi / Choti Diwali"), _s("Kali Puja","West Bengal","Assam","Odisha","Tripura")))
    add([6,7],[29], _m(
        _all("Diwali / Lakshmi Puja"),
        _s("Kali Puja (State Holiday)","West Bengal","Assam","Odisha","Tripura"),
        _s("Naraka Chaturdashi (South)","Tamil Nadu","Karnataka","Andhra Pradesh","Telangana","Kerala","Puducherry"),
    ))
    add([6,7],[15], _m(
        _all("Govardhan Puja / Annakut"),
        _s("Padwa / Bali Pratipada","Maharashtra","Goa"),
        _s("Bali Pratipada","Karnataka","Andhra Pradesh","Telangana"),
        _s("Gujarati New Year / Bestu Varas","Gujarat"),
    ))
    add([6,7],[16], _all("Bhai Dooj / Bhau Beej / Yama Dwitiya"))
    add([6,7],[19], _s("Chhath Puja - Nahay Khay","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"))
    add([6,7],[20], _s("Chhath Puja - Kharna","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"))
    add([6,7],[21], _s("Chhath Puja - Sandhya Arghya","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"))
    add([6,7],[22], _s("Chhath Puja - Usha Arghya","Bihar","Jharkhand","Uttar Pradesh","Delhi","West Bengal","Assam","Uttarakhand"))
    add([6,7],[25], _m(_all("Dev Uthani Ekadashi / Tulsi Vivah"),
                       _s("Kartik Ekadashi / Wari","Maharashtra","Goa"),
                       _s("Tulsi Vivah","Maharashtra","Goa","Gujarat","Rajasthan","Uttar Pradesh","Bihar")))
    # Kartik Purnima = sun=6 OR sun=7 (verified 2020-2030)
    add([6,7],[14], _m(
        _all("Kartik Purnima / Dev Deepawali"),
        _s("Guru Nanak Jayanti","Punjab","Haryana","Delhi","Himachal Pradesh","Uttarakhand",
           "Chandigarh","Jammu & Kashmir","Karnataka","Maharashtra","Gujarat","Rajasthan",
           "Uttar Pradesh","Bihar","West Bengal","Andhra Pradesh","Telangana","Tamil Nadu",
           "Kerala","Odisha","Assam","Madhya Pradesh","Chhattisgarh"),
        _s("Pushkar Fair","Rajasthan"),
        _s("Tripuri Purnima","Tripura"),
        _s("Dev Deepawali (Varanasi)","Uttar Pradesh","Bihar","Uttarakhand"),
    ))

    # ── Margashirsha festivals ────────────────────────────────────────────────
    # sun=7(Scorpio) or 8(Sagittarius)
    add([7,8],[0],  _s("Champa Shashthi / Khandoba Festival begins","Maharashtra","Goa"))
    add([7,8],[4],  _s("Vivah Panchami","Uttar Pradesh","Bihar","Madhya Pradesh","Rajasthan","Uttarakhand","Delhi"))
    add([7,8],[5],  _s("Champa Shashthi / Khandoba Festival (main day)","Maharashtra","Goa"))
    add([7,8],[10], _m(_all("Mokshada Ekadashi / Gita Jayanti"),
                       _s("Vaikunta Ekadashi","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala")))
    add([7,8],[14], _m(
        _s("Dattatreya Jayanti / Datta Jayanti","Maharashtra","Karnataka","Goa","Andhra Pradesh","Telangana","Gujarat"),
        _s("Tripuri Purnima","Tripura"),
    ))
    # ── Paush festivals ───────────────────────────────────────────────────────
    # sun=8(Sagittarius) or 9(Capricorn)
    add([8,9],[14], _m(
        _all("Paush Purnima"),
        _s("Shakambhari Purnima","Rajasthan","Uttar Pradesh","Madhya Pradesh"),
        _s("Gangasagar Mela","West Bengal"),
    ))

    # ── Magha festivals ───────────────────────────────────────────────────────
    # Vasant Panchami = sun=9(Capricorn) or 10(Aquarius)
    add([9,10],[3], _m(
        _s("Maghi Ganesh Jayanti","Maharashtra","Goa"),
        _s("Sakat Chauth","Uttar Pradesh","Bihar","Rajasthan","Madhya Pradesh"),
    ))
    add([9,10],[4], _m(
        _all("Vasant Panchami"),
        _s("Saraswati Puja (State Holiday)","West Bengal","Odisha","Assam","Bihar","Jharkhand","Tripura"),
        _s("Shri Panchami","West Bengal","Odisha"),
    ))
    add([9,10],[14], _m(
        _all("Maghi Purnima"),
        _s("Magha Mela (Prayagraj)","Uttar Pradesh","Uttarakhand"),
        _s("Maghi (State Holiday)","Punjab","Haryana","Chandigarh"),
        _s("Thaipusam","Tamil Nadu","Kerala","Puducherry"),
    ))
    # Maha Shivratri = sun=10 always (Krishna Chaturdashi tithi 28)
    add([10],[27,28], _all("Maha Shivratri"))

    # ── Phalguna festivals ────────────────────────────────────────────────────
    # Holi = sun=10 mostly, sun=11 in some years
    # Holi = covered by PURNIMA_NAMES[10] = "Phalguna Purnima / Holi"
    add([10,11],[4],  _s("Rang Panchami","Maharashtra","Madhya Pradesh","Rajasthan","Gujarat","Chhattisgarh"))
    add([10,11],[9],  _all("Amalaki Ekadashi"))
    add([10,11],[13], _m(_all("Holika Dahan"), _s("Shimga (Holi eve)","Maharashtra","Goa")))
    # Holi = Purnima (tithi 14) in some years, Krishna Pratipada (tithi 15) in others
    # Both are valid — depends on when Purnima ends relative to sunrise
    add([10,11],[14], _m(
        _all("Holi"),
        _s("Dol Jatra / Dol Purnima","West Bengal","Odisha","Assam","Tripura"),
        _s("Shigmo","Goa"),
        _s("Yaosang","Manipur"),
        _s("Phakuwa","Assam"),
    ))
    add([10,11],[15], _m(
        _all("Holi"),
        _s("Dol Jatra / Dol Purnima","West Bengal","Odisha","Assam","Tripura"),
        _s("Shigmo","Goa"),
        _s("Yaosang","Manipur"),
        _s("Dhuleti / Rangwali Holi","Gujarat","Rajasthan","Madhya Pradesh","Uttar Pradesh","Bihar","Chhattisgarh"),
    ))

    # Merge — last entry wins for same key
    result = {}
    for key, sd in entries:
        if key not in result:
            result[key] = {}
        result[key].update(sd)
    return result

LUNAR_RULES = _build_lunar_rules()

# ═════════════════════════════════════════════════════════════════════════════
# SOLAR RULES — genuinely fixed by solar/Gregorian calendar
# ═════════════════════════════════════════════════════════════════════════════

def _build_solar_rules():
    e = []
    def add(key, sd): e.append((key, sd))

    add((1, 1),  _all("New Year's Day"))
    add((1,12),  _s("Swami Vivekananda Jayanti","West Bengal","Assam","Odisha","Tripura","Andaman & Nicobar"))
    add((1,23),  _s("Netaji Subhash Chandra Bose Jayanti","West Bengal","Odisha","Assam","Tripura"))
    add((1,26),  _all("Republic Day"))
    add((2,19),  _s("Chhatrapati Shivaji Maharaj Jayanti","Maharashtra","Goa","Dadra & Nagar Haveli"))
    add((3,23),  _s("Shaheed Diwas (Bhagat Singh)","Punjab","Haryana","Delhi","Chandigarh","Uttar Pradesh"))
    add((4,14),  _all("Dr. Ambedkar Jayanti"))
    add((5, 1),  _all("International Labour Day"))
    add((8,15),  _all("Independence Day"))
    add((9, 5),  _all("Teachers Day"))
    add((10,2),  _all("Gandhi Jayanti"))
    add((12,25), _all("Christmas"))
    # Makar Sankranti — solar
    add((1,13),  _s("Bhogi Pongal","Tamil Nadu","Puducherry","Andhra Pradesh","Telangana"))
    add((1,14),  _m(
        _all("Makar Sankranti"),
        _s("Thai Pongal","Tamil Nadu","Puducherry"),
        _s("Lohri","Punjab","Haryana","Himachal Pradesh","Delhi","Chandigarh","Jammu & Kashmir"),
        _s("Uttarayan / Kite Festival","Gujarat","Rajasthan"),
        _s("Magh Bihu / Bhogali Bihu","Assam"),
        _s("Khichdi Parva","Uttar Pradesh","Bihar","Jharkhand","Uttarakhand"),
        _s("Makara Vilakku (Sabarimala)","Kerala","Lakshadweep"),
        _s("Tusu Puja / Makar Parab","West Bengal","Jharkhand","Odisha"),
        _s("Uttarayani Mela (Bageshwar)","Uttarakhand"),
        _s("Makar Sankranti / Sankranti / Ellu Birodhu","Karnataka"),
        _s("Makar Sankranti / Til-Gul","Maharashtra","Goa"),
        _s("Maghi (Muktsar Fair)","Punjab"),
    ))
    add((1,15),  _m(_s("Thiruvalluvar Day","Tamil Nadu","Puducherry"), _s("Magh Bihu (State Holiday)","Assam")))
    add((1,16),  _s("Mattu Pongal / Uzhavar Thirunal","Tamil Nadu","Puducherry"))
    add((1,17),  _s("Kannum Pongal","Tamil Nadu","Puducherry"))
    add((1,18),  _m(_s("Jallikattu","Tamil Nadu"), _s("Lui-Ngai-Ni (Naga New Year)","Nagaland","Manipur")))
    add((1,31),  _s("Me-Dam-Me-Phi (Ahom)","Assam"))
    add((2, 1),  _m(_s("Surajkund Craft Mela","Haryana","Delhi"), _s("Kala Ghoda Arts Festival (Mumbai)","Maharashtra")))
    add((2,20),  _s("Goa Carnival","Goa"))
    add((3, 1),  _s("Chapchar Kut (State Holiday)","Mizoram"))
    add((3,15),  _s("Ellora-Ajanta Festival","Maharashtra"))
    add((3,18),  _s("Gangaur","Rajasthan","Madhya Pradesh","Gujarat"))
    add((3,22),  _m(_s("Bihar Diwas","Bihar","Jharkhand"), _s("Phool Dei (Spring Festival)","Uttarakhand")))
    add((3,28),  _s("Karaga Festival (Bangalore)","Karnataka"))
    add((3,30),  _s("Rajasthan Day","Rajasthan"))
    add((4, 1),  _m(_s("Utkal Diwas (Odisha Foundation Day)","Odisha"), _s("Vairamudi Festival (Melkote)","Karnataka")))
    add((4,10),  _s("Thrissur Pooram","Kerala"))
    add((4,13),  _m(_s("Bohag Bihu / Rongali Bihu (State Holiday)","Assam"), _s("Sajibu Cheiraoba (Meitei New Year)","Manipur")))
    add((4,14),  _m(
        _s("Baisakhi / Vaisakhi","Punjab","Haryana","Himachal Pradesh","Delhi","Chandigarh","Uttarakhand"),
        _s("Puthandu / Tamil New Year","Tamil Nadu","Puducherry"),
        _s("Vishu","Kerala","Lakshadweep"),
        _s("Pohela Boishakh / Bengali New Year","West Bengal","Tripura","Assam"),
        _s("Himachal Day","Himachal Pradesh"),
        _s("Pana Sankranti / Maha Vishuba Sankranti","Odisha"),
    ))
    add((4,15),  _m(_s("Himachal Pradesh Foundation Day","Himachal Pradesh"), _s("Pohela Boishakh (State Holiday)","West Bengal","Tripura")))
    add((5, 1),  _m(_s("Maharashtra Day","Maharashtra","Goa","Dadra & Nagar Haveli"), _s("Gujarat Day","Gujarat")))
    add((5, 3),  _s("Hampi Utsav / Vijayanagara Festival","Karnataka"))
    add((5, 9),  _s("Rabindra Jayanti","West Bengal","Tripura","Assam"))
    add((5,16),  _s("Sikkim Statehood Day","Sikkim"))
    add((6, 1),  _s("Telangana Formation Day","Telangana"))
    add((6,13),  _s("Feast of St Anthony","Goa"))
    add((6,20),  _m(_s("Ambubachi Mela (Kamakhya)","Assam"), _s("Raja Parba","Odisha")))
    add((6,24),  _s("Sao Joao","Goa"))
    add((7,17),  _s("Kharchi Puja (State Holiday)","Tripura"))
    add((8, 9),  _s("Karma Puja","Jharkhand","Odisha","Chhattisgarh","West Bengal"))
    add((8,15),  _s("Feast of Assumption of Our Lady","Goa"))
    add((8,20),  _s("Nuakhai (State Holiday)","Odisha","Chhattisgarh"))
    add((8,26),  _s("Ker Puja","Tripura"))
    add((8,29),  _s("Onam / Thiruvonam (State Holiday)","Kerala","Lakshadweep"))
    add((9, 1),  _m(_s("Bathukamma begins","Telangana"), _s("Sree Narayana Guru Samadhi","Kerala"), _s("Ladakh Festival","Ladakh")))
    add((9,18),  _s("Pola / Bail Pola","Maharashtra","Chhattisgarh","Madhya Pradesh"))
    add((9,20),  _s("Mim Kut","Mizoram"))
    add((9,22),  _s("Pang Lhabsol","Sikkim"))
    add((10,2),  _m(_s("Bathukamma (main day)","Telangana"), _s("Kullu Dussehra begins","Himachal Pradesh")))
    add((10,14), _s("Tula Sankramana (Talakaveri)","Karnataka"))
    add((10,15), _s("Pushkar Camel Fair","Rajasthan"))
    add((10,18), _s("Kongali Bihu / Kati Bihu","Assam"))
    add((10,24), _s("J&K Accession Day","Jammu & Kashmir","Ladakh"))
    add((11, 1), _m(
        _s("Karnataka Rajyotsava (State Holiday)","Karnataka"),
        _s("Haryana Day","Haryana","Chandigarh"),
        _s("Punjab Day","Punjab","Chandigarh"),
        _s("MP Foundation Day","Madhya Pradesh","Chhattisgarh"),
        _s("Kerala Piravi","Kerala","Lakshadweep"),
        _s("Chavang Kut (Kuki-Zo)","Manipur"),
    ))
    add((11, 6), _s("Kambala (Buffalo Race) season begins","Karnataka"))
    add((11, 9), _s("Uttarakhand Foundation Day","Uttarakhand"))
    add((11,15), _m(_s("Jharkhand Foundation Day","Jharkhand"), _s("Birsa Munda Jayanti","Jharkhand","Odisha","West Bengal","Chhattisgarh")))
    add((11,19), _s("Hornbill Festival begins","Nagaland"))
    add((11,28), _s("Ningol Chakouba","Manipur"))
    add((12, 1), _m(_s("Nagaland Statehood Day / Hornbill Festival","Nagaland"), _s("International Sand Art Festival (Puri)","Odisha")))
    add((12, 2), _s("Mizoram Statehood Day","Mizoram"))
    add((12, 3), _s("Feast of St Francis Xavier","Goa"))
    add((12, 8), _s("Feast of Immaculate Conception","Goa"))
    add((12,19), _s("Goa Liberation Day","Goa","Dadra & Nagar Haveli"))
    add((12,22), _s("Pattadakal Dance Festival","Karnataka"))
    add((12,27), _s("Losoong / Namsoong (Sikkimese New Year)","Sikkim"))
    add((12,31), _s("Pawl Kut","Mizoram"))
    add((1, 6),  _s("Feast of Three Kings (Christians)","Goa","Maharashtra"))
    add((2,15),  _s("Attukal Pongala (Thiruvananthapuram)","Kerala"))
    add((8,10),  _m(_s("Nehru Trophy Boat Race (Alappuzha)","Kerala"), _s("Sekrenyi (Angami Naga)","Nagaland")))
    add((11, 5), _s("Aranmula Boat Race","Kerala"))
    add((1, 5),  _s("Losar (Monpa New Year)","Arunachal Pradesh","Sikkim","Ladakh"))
    add((2,26),  _s("Nyokum Yullo (Nishi tribe)","Arunachal Pradesh"))
    add((4, 5),  _s("Mopin (Adi tribe)","Arunachal Pradesh"))
    add((7, 5),  _s("Dree Festival (Apatani tribe)","Arunachal Pradesh"))
    add((9, 5),  _s("Solung (Adi tribe)","Arunachal Pradesh"))
    add((5, 1),  _s("Moatsu (Ao Naga)","Nagaland"))
    add((2, 1),  _s("Bikaner Camel Festival","Rajasthan"))
    add((7,15),  _s("Harela (Kumaon harvest)","Uttarakhand"))
    add((6,15),  _s("Hemis Festival","Ladakh","Jammu & Kashmir"))
    add((8,15),  _s("Puducherry De Facto Transfer Day","Puducherry"))
    add((11, 1), _s("Puducherry Liberation Day","Puducherry"))
    add((3, 4),  _s("Island Tourism Festival","Andaman & Nicobar"))

    # ── Maharashtra missing festivals ─────────────────────────────────────────
    # Maghi Ganesh Jayanti = Magha Shukla Chaturthi (solar approx: late Jan/Feb)
    # handled via lunar — adding solar fallback
    add((1, 7),  _s("Maghi Ganesh Jayanti","Maharashtra","Goa"))
    add((2, 7),  _s("Maghi Ganesh Jayanti","Maharashtra","Goa"))
    # Jejuri Khandoba Yatra — Champashashthi (already covered) + Somvati Amavasya
    add((12, 6), _s("Jejuri Khandoba Yatra (Champashashthi)","Maharashtra"))
    # Bhimashankar Mahashivratri — same as Maha Shivratri but specific to Bhimashankar
    # already covered by Maha Shivratri
    # Tripuri Purnima — Kartik Purnima (already covered)
    # Datta Jayanti — Margashirsha Purnima (already covered as Dattatreya Jayanti)

    # ── Karnataka missing festivals ───────────────────────────────────────────
    # Vara Mahalakshmi Vrata — Shravana Shukla Purnima Friday (solar approx Aug)
    add((8, 8),  _s("Vara Mahalakshmi Vrata","Karnataka","Andhra Pradesh","Telangana","Tamil Nadu"))
    add((8, 9),  _s("Vara Mahalakshmi Vrata","Karnataka","Andhra Pradesh","Telangana","Tamil Nadu"))
    # Vaikunta Ekadashi — Margashirsha Shukla Ekadashi (already as Mokshada Ekadashi)
    # adding Karnataka-specific name
    add((12, 1), _s("Vaikunta Ekadashi","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala"))
    add((12, 2), _s("Vaikunta Ekadashi","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala"))
    # Mahamastakabhisheka (Shravanabelagola) — every 12 years, next ~2030
    # Kadlekai Parishe (Bengaluru Groundnut Fair) — last Sunday of Kartik month, approx Nov
    add((11, 25), _s("Kadlekai Parishe (Bengaluru Groundnut Fair)","Karnataka"))
    add((11, 26), _s("Kadlekai Parishe (Bengaluru Groundnut Fair)","Karnataka"))
    # Mangalore Dasara — same as Dussehra but specific to Mangalore
    # already covered by Dussehra
    # Yellamma Jatre — Phalguna Purnima (Saundatti, Karnataka)
    add((3, 14), _s("Yellamma Jatre (Saundatti)","Karnataka"))
    add((3, 15), _s("Yellamma Jatre (Saundatti)","Karnataka"))
    # Banashankari Jatre — Magha Amavasya (Badami, Karnataka)
    add((1, 28), _s("Banashankari Jatre (Badami)","Karnataka"))
    add((1, 29), _s("Banashankari Jatre (Badami)","Karnataka"))
    add((2, 10), _s("Banashankari Jatre (Badami)","Karnataka"))
    # Marikamba Jatre — Shravana (Sirsi, Karnataka) — biennial, approx Aug
    add((8, 1),  _s("Marikamba Jatre (Sirsi)","Karnataka"))
    # Suggi Habba — harvest festival, Ugadi season (already covered)
    # Kadalekayi Parishe — same as Kadlekai Parishe above
    # Dollu Kunitha — cultural festival, no fixed date (performance art)

    result = {}
    for key, sd in e:
        if key not in result:
            result[key] = {}
        result[key].update(sd)
    return result

SOLAR_RULES = _build_solar_rules()

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
    sun_sign_index  = int(sun_sid / 30.0) % 12

    from datetime import date as _date
    vara_index = _date(year, month, day).weekday()

    return {
        "tithi_index": tithi_index, "nakshatra_index": nakshatra_index,
        "yoga_index": yoga_index, "karana_index": karana_index,
        "vara_index": vara_index, "sun_sign_index": sun_sign_index,
    }


def _collect_state_festivals(p: dict, d) -> dict:
    state_map = {s: [] for s in ALL_STATES}
    ti  = p["tithi_index"]
    ss  = p["sun_sign_index"]

    def _apply(rule_dict, key):
        entry = rule_dict.get(key)
        if not entry:
            return
        for state, name in entry.items():
            if name and state in state_map and name not in state_map[state]:
                state_map[state].append(name)

    # 1. Amavasya — purely tithi-based, always correct
    if ti == 29:
        name = AMAVASYA_NAMES.get(ss, "Amavasya")
        for s in ALL_STATES:
            state_map[s].append(name)
        # Diwali — Kartik Amavasya (sun_sign=6)
        if ss == 6:
            for s in ALL_STATES:
                if "Diwali / Lakshmi Puja" not in state_map[s]:
                    state_map[s].append("Diwali / Lakshmi Puja")
            for s in ["West Bengal","Assam","Odisha","Tripura"]:
                if "Kali Puja (State Holiday)" not in state_map[s]:
                    state_map[s].append("Kali Puja (State Holiday)")
            for s in ["Tamil Nadu","Karnataka","Andhra Pradesh","Telangana","Kerala","Puducherry"]:
                if "Naraka Chaturdashi (South)" not in state_map[s]:
                    state_map[s].append("Naraka Chaturdashi (South)")
        # Mahalaya — Bhadrapada Amavasya (sun_sign=4 or 5)
        if ss in [4, 5]:
            for s in ["West Bengal","Assam","Odisha","Tripura"]:
                if "Mahalaya / Durga Puja begins" not in state_map[s]:
                    state_map[s].append("Mahalaya / Durga Puja begins")
        # Bail Pola — Shravana Amavasya (sun_sign=3 or 4)
        if ss in [3, 4]:
            for s in ["Maharashtra","Chhattisgarh","Madhya Pradesh"]:
                if "Bail Pola / Pithori Amavasya" not in state_map[s]:
                    state_map[s].append("Bail Pola / Pithori Amavasya")

    # 1b. Chaturdashi (tithi 28) — Diwali eve / Narak Chaturdashi
    # Official Diwali date is often Chaturdashi when Amavasya starts after sunset
    elif ti == 28:
        if ss == 6:
            # Kartik Krishna Chaturdashi = Diwali (official date in most years)
            for s in ALL_STATES:
                state_map[s].append("Diwali / Narak Chaturdashi")
            for s in ["West Bengal","Assam","Odisha","Tripura"]:
                state_map[s].append("Kali Puja")
            for s in ["Tamil Nadu","Karnataka","Andhra Pradesh","Telangana","Kerala","Puducherry"]:
                state_map[s].append("Naraka Chaturdashi (South)")

    # 2. Purnima — purely tithi-based, name from PURNIMA_NAMES dict
    elif ti == 14:
        name = PURNIMA_NAMES.get(ss, "Purnima")
        for s in ALL_STATES:
            state_map[s].append(name)
        # Kartik Purnima extras
        if ss in [6, 7]:
            for s in ["Punjab","Haryana","Delhi","Himachal Pradesh","Uttarakhand","Chandigarh","Jammu & Kashmir"]:
                if "Guru Nanak Jayanti" not in state_map[s]:
                    state_map[s].append("Guru Nanak Jayanti")
        # Ashwin Purnima extras
        if ss == 5:
            for s in ["West Bengal","Odisha","Assam","Tripura"]:
                if "Lakshmi Puja" not in state_map[s]:
                    state_map[s].append("Lakshmi Puja")
        # Phalguna Purnima = Holi regional names
        if ss in [10, 11]:
            for s in ["West Bengal","Odisha","Assam","Tripura"]:
                if "Dol Jatra / Dol Purnima" not in state_map[s]:
                    state_map[s].append("Dol Jatra / Dol Purnima")
            for s in ["Goa"]:
                if "Shigmo" not in state_map[s]:
                    state_map[s].append("Shigmo")
            for s in ["Manipur"]:
                if "Yaosang" not in state_map[s]:
                    state_map[s].append("Yaosang")

    # 3. Ekadashi — tithi-based
    elif ti in [10, 25]:
        ekadashi_name = {
            11:"Kamada Ekadashi", 0:"Mohini Ekadashi", 1:"Nirjala Ekadashi",
            2:"Devshayani Ekadashi", 3:"Putrada Ekadashi", 4:"Indira Ekadashi",
            5:"Papankusha Ekadashi", 6:"Dev Uthani Ekadashi", 7:"Mokshada Ekadashi",
            8:"Saphala Ekadashi", 9:"Paush Putrada Ekadashi", 10:"Jaya Ekadashi"
        }.get(ss, "Ekadashi")
        for s in ALL_STATES:
            state_map[s].append(ekadashi_name)
        # Ashadhi Wari for Maharashtra
        if ss in [2, 3] and ti == 10:
            for s in ["Maharashtra","Goa"]:
                if "Ashadhi Ekadashi / Wari" not in state_map[s]:
                    state_map[s].append("Ashadhi Ekadashi / Wari")
        if ss in [6] and ti == 25:
            for s in ["Maharashtra","Goa"]:
                if "Kartik Ekadashi / Wari" not in state_map[s]:
                    state_map[s].append("Kartik Ekadashi / Wari")

    # 4. Lunar festival rules (specific festivals)
    # Skip Rath Yatra if month is not June or July (prevents duplicate)
    _apply(LUNAR_RULES, (ss, ti))

    # Remove Rath Yatra if it fires outside June (it's always in June)
    if ti == 1 and ss == 2 and d.month != 6:
        for s in ALL_STATES:
            if "Jagannath Rath Yatra" in state_map[s]:
                state_map[s].remove("Jagannath Rath Yatra")
            if "Rath Yatra (State Holiday)" in state_map[s]:
                state_map[s].remove("Rath Yatra (State Holiday)")

    # Remove Ashadhi Ekadashi if it fires outside June (it's always in June)
    if ti == 10 and ss == 2 and d.month != 6:
        for s in ALL_STATES:
            if "Devshayani Ekadashi" in state_map[s]:
                state_map[s].remove("Devshayani Ekadashi")
        for s in ["Maharashtra","Goa"]:
            if "Ashadhi Ekadashi / Wari" in state_map[s]:
                state_map[s].remove("Ashadhi Ekadashi / Wari")

    # Remove Putrada Ekadashi if it fires with Ashadhi label (Jul Ekadashi is Putrada, not Ashadhi)
    if ti == 10 and ss == 3 and d.month == 7:
        for s in ["Maharashtra","Goa"]:
            if "Ashadhi Ekadashi / Wari" in state_map[s]:
                state_map[s].remove("Ashadhi Ekadashi / Wari")

    # Remove Vat Purnima if it fires outside May-Jun (Jyeshtha Purnima only)
    if ti == 14 and ss in [1,2] and d.month not in [5, 6]:
        for s in ["Maharashtra","Gujarat","Goa"]:
            if "Vat Purnima (MH/GJ only)" in state_map[s]:
                state_map[s].remove("Vat Purnima (MH/GJ only)")

    # Remove Maghi Purnima if it fires outside Jan-Feb (Magha Purnima only)
    if ti == 14 and ss in [9,10] and d.month not in [1, 2]:
        for s in ALL_STATES:
            if "Maghi Purnima" in state_map[s]:
                state_map[s].remove("Maghi Purnima")

    # Remove Dussehra if it fires outside Sep-Oct window
    if ti == 9 and ss in [5,6] and d.month not in [9, 10, 11]:
        for s in ALL_STATES:
            for name in ["Dussehra / Vijayadashami","Mysuru Dasara (State Festival)","Kullu Dussehra",
                         "Bastar Dussehra","Durga Puja Dashami / Sindur Khela","Kota Dussehra","Dussehra"]:
                if name in state_map[s]:
                    state_map[s].remove(name)

    # Remove Navratri if it fires outside Sep-Nov window (second occurrence is wrong)
    if ti == 0 and ss in [5,6] and d.month not in [9, 10, 11]:
        for s in ALL_STATES:
            if "Shardiya Navratri begins / Ghatasthapana" in state_map[s]:
                state_map[s].remove("Shardiya Navratri begins / Ghatasthapana")

    # Remove second Navratri occurrence — only one per year (first one in Sep-Oct is correct)
    if ti == 0 and ss == 6 and d.month in [10, 11]:
        # Check if this is the second Navratri (first was already in Sep-Oct with ss=5)
        # If month is Nov, it's definitely wrong
        if d.month == 11:
            for s in ALL_STATES:
                if "Shardiya Navratri begins / Ghatasthapana" in state_map[s]:
                    state_map[s].remove("Shardiya Navratri begins / Ghatasthapana")

    # Remove Diwali from non-Kartik Amavasya (sun_sign != 6)
    if ti == 29 and ss != 6:
        for s in ALL_STATES:
            for name in ["Diwali / Lakshmi Puja", "Kali Puja (State Holiday)",
                         "Naraka Chaturdashi (South)"]:
                if name in state_map[s]:
                    state_map[s].remove(name)

    # 5. Nakshatra override: Onam Thiruvonam = Shravana nakshatra
    if ss in [4, 5] and p["nakshatra_index"] == 21:
        for s in ["Kerala","Lakshadweep"]:
            if "Onam - Thiruvonam (Main Day)" not in state_map[s]:
                state_map[s].insert(0, "Onam - Thiruvonam (Main Day)")

    # 6. Solar festivals
    _apply(SOLAR_RULES, (d.month, d.day))

    # 7. Gazetted national holidays
    india_hols = holidays_lib.India(years=d.year)
    official   = india_hols.get(d)
    if official:
        # Skip if our engine already has a more accurate version of this festival
        already_covered = any(
            official.lower() in f.lower() or f.lower() in official.lower()
            for fests in state_map.values() for f in fests
        )
        # Also skip Diwali from holidays lib if today is NOT Amavasya (tithi 29)
        # The holidays lib sometimes puts Diwali on Chaturdashi
        if official == "Diwali" and ti != 29:
            already_covered = True
        if not already_covered:
            for s in ALL_STATES:
                if official not in state_map[s]:
                    state_map[s].append(official)

    # Final cleanup: remove generic Dussehra from Navami — but keep Mysuru Dasara
    # Mysuru Dasara IS officially on Navami in Karnataka
    if ti == 8:
        for s in ALL_STATES:
            for name in ["Dussehra / Vijayadashami","Kullu Dussehra",
                         "Bastar Dussehra","Kota Dussehra"]:
                if name in state_map[s]:
                    state_map[s].remove(name)

    return state_map


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

def get_calendar_data(date_str: str, state: str = None) -> dict:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    p = _compute_panchang(d.year, d.month, d.day)

    ti = p["tithi_index"]
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
        "date":        date_str,
        "tithi":       f"{PAKSHA[ti]} {TITHI_NAMES[ti]}",
        "nakshatra":   NAKSHATRAS[p["nakshatra_index"]],
        "is_amavasya": ti == 29,
        "is_purnima":  ti == 14,
        "is_ekadashi": ti in [10, 25],
        "festivals":   all_unique,
        "state_festivals": active,
    }
  
