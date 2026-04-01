"""
calendar_engine.py — Kalnirnay-style Panchang engine for Crop Price Prediction
Five angas: Tithi, Vara, Nakshatra, Yoga, Karana

Festival detection strategy:
  LUNAR_RULES  → (sun_sign_index, tithi_index) — covers BOTH adjacent signs per festival
                 so the same festival is detected correctly across ALL years
  SOLAR_RULES  → (month, day) — genuinely solar/fixed festivals (Sankranti, Baisakhi etc.)
  Gazetted     → `holidays` library

Crop demand signals included for ML models.
Focus: Maharashtra + Karnataka local festivals, all Amavasya/Purnima/Ekadashi.
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

def _all(name):  return {s: name for s in ALL_STATES}
def _s(name, *states): return {s: name for s in states}
def _m(*dicts):
    out = {}
    for d in dicts: out.update(d)
    return out

# ═════════════════════════════════════════════════════════════════════════════
# LUNAR RULES
# Key: (sun_sign_index 0-11, tithi_index 0-29)
# Each festival covers BOTH adjacent sun-sign values → works for ALL years
# ═════════════════════════════════════════════════════════════════════════════

def _build_lunar_rules():
    entries = []
    def add(lm_list, ti_list, sd):
        for lm in lm_list:
            for ti in ti_list:
                entries.append(((lm % 12, ti), sd))

    # ── Every Amavasya (tithi 29) — tagged for all months ────────────────────
    for lm in range(12):
        add([lm],[29], _m(
            _all("Amavasya"),
            # Month-specific Amavasya names
            {s: {
                11:"Chaitra Amavasya", 0:"Vaishakha Amavasya",
                1:"Jyeshtha Amavasya / Shani Amavasya",
                2:"Ashadha Amavasya", 3:"Shravana Amavasya / Bail Pola",
                4:"Bhadrapada Amavasya / Mahalaya", 5:"Ashwin Amavasya",
                6:"Kartik Amavasya / Diwali", 7:"Margashirsha Amavasya",
                8:"Paush Amavasya", 9:"Magha Amavasya",
                10:"Phalguna Amavasya"
            }.get(lm, "Amavasya") for s in ALL_STATES}
        ))

    # ── Every Purnima (tithi 14) — tagged for all months ─────────────────────
    for lm in range(12):
        add([lm],[14], _m(
            _all("Purnima"),
            {s: {
                11:"Chaitra Purnima / Hanuman Jayanti",
                0:"Vaishakha Purnima / Buddha Purnima",
                1:"Jyeshtha Purnima / Vat Purnima",
                2:"Ashadha Purnima / Guru Purnima",
                3:"Shravana Purnima / Raksha Bandhan",
                4:"Bhadrapada Purnima",
                5:"Ashwin Purnima / Sharad Purnima / Kojagiri",
                6:"Kartik Purnima / Dev Deepawali",
                7:"Margashirsha Purnima / Dattatreya Jayanti",
                8:"Paush Purnima",
                9:"Magha Purnima / Maghi",
                10:"Phalguna Purnima / Holi"
            }.get(lm, "Purnima") for s in ALL_STATES}
        ))

    # ── Every Ekadashi (tithi 10 Shukla + tithi 25 Krishna) ──────────────────
    for lm in range(12):
        add([lm],[10], _all("Shukla Ekadashi"))
        add([lm],[25], _all("Krishna Ekadashi"))

    # ── Every Chaturdashi (tithi 13 Shukla + tithi 28 Krishna) ───────────────
    for lm in range(12):
        add([lm],[13], _all("Shukla Chaturdashi"))
        add([lm],[28], _all("Krishna Chaturdashi / Masik Shivratri"))

    # ── Gudi Padwa / Ugadi — Chaitra Shukla Pratipada (Sun Pisces/Aries) ─────
    add([11,0],[0,1], _m(
        _s("Gudi Padwa","Maharashtra","Goa","Dadra & Nagar Haveli"),
        _s("Ugadi","Karnataka","Andhra Pradesh","Telangana"),
        _s("Cheti Chand","Rajasthan","Gujarat","Delhi","Madhya Pradesh","Chandigarh"),
        _s("Navreh","Jammu & Kashmir","Ladakh"),
        _s("Sajibu Nongma Panba","Manipur"),
        _s("Chaitra Navratri begins","Uttar Pradesh","Bihar","Jharkhand","Uttarakhand",
           "Himachal Pradesh","Haryana","Punjab","Rajasthan","Madhya Pradesh","Chhattisgarh","Delhi"),
    ))
    add([11,0],[2], _s("Chaitri Gaur begins (married women festival)","Maharashtra","Goa"))
    add([11,0],[5], _s("Yamuna Chhath","Uttar Pradesh","Bihar","Delhi","Uttarakhand"))
    add([11,0],[7], _m(
        _s("Chaitra Ashtami","West Bengal","Odisha","Assam","Tripura"),
        _s("Sheetala Ashtami","Uttar Pradesh","Rajasthan","Haryana","Punjab","Delhi"),
    ))
    add([11,0],[8], _all("Ram Navami"))
    add([11,0],[13], _all("Mahavir Jayanti"))

    # ── Akshaya Tritiya / Basava Jayanti (Sun Aries/Taurus) ──────────────────
    add([0,1],[1,2], _m(
        _all("Akshaya Tritiya"),
        _s("Parashurama Jayanti","Kerala","Karnataka","Maharashtra","Goa","Andhra Pradesh","Telangana"),
        _s("Basava Jayanti","Karnataka","Andhra Pradesh","Telangana"),
    ))
    add([0,1],[4], _s("Shankaracharya Jayanti","Kerala","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana"))
    add([0,1],[8], _s("Sita Navami","Uttar Pradesh","Bihar","Jharkhand","Madhya Pradesh","Uttarakhand","Rajasthan"))

    # ── Jyeshtha festivals (Sun Taurus/Gemini) ────────────────────────────────
    add([1,2],[5], _s("Skanda Sashti","Tamil Nadu","Puducherry","Kerala","Karnataka","Andhra Pradesh","Telangana"))
    add([1,2],[9], _s("Ganga Dussehra","Uttar Pradesh","Uttarakhand","Bihar","Jharkhand","Delhi","Madhya Pradesh","Rajasthan"))
    add([1,2],[10], _m(
        _s("Vat Savitri Puja","Maharashtra","Goa","Gujarat","Bihar","Jharkhand","Uttar Pradesh","Madhya Pradesh","Rajasthan"),
        _s("Nirjala Ekadashi","Uttar Pradesh","Bihar","Rajasthan","Delhi","Uttarakhand"),
    ))
    add([1,2],[14], _s("Vat Purnima","Maharashtra","Gujarat","Goa"))

    # ── Ashadha festivals (Sun Gemini/Cancer) ─────────────────────────────────
    add([2,3],[1], _m(_all("Jagannath Rath Yatra"), _s("Rath Yatra (State Holiday)","Odisha")))
    add([2,3],[5], _s("Skanda Sashti","Tamil Nadu","Puducherry","Andhra Pradesh","Telangana"))
    add([2,3],[10], _m(_all("Devshayani Ekadashi"), _s("Ashadhi Ekadashi / Wari","Maharashtra","Goa")))

    # ── Shravana festivals (Sun Cancer/Leo) ───────────────────────────────────
    add([3,4],[2], _s("Hariyali Teej","Rajasthan","Uttar Pradesh","Haryana","Punjab","Delhi",
                      "Madhya Pradesh","Bihar","Uttarakhand","Himachal Pradesh","Chandigarh"))
    add([3,4],[4], _all("Nag Panchami"))
    add([3,4],[6], _s("Mangala Gaur (Shravana Tuesday)","Maharashtra","Goa"))
    add([3,4],[7], _s("Tulsi Shravana Saptami","Maharashtra","Gujarat"))
    add([3,4],[11], _s("Onam - Atham (Day 1)","Kerala","Lakshadweep"))
    add([3,4],[13,14], _m(
        _all("Raksha Bandhan"),
        _s("Narali Purnima / Coconut Festival","Maharashtra","Goa"),
        _s("Avani Avittam / Upakarma","Tamil Nadu","Kerala","Puducherry"),
        _s("Jhulan Purnima / Jhulana Yatra","West Bengal","Odisha","Assam"),
        _s("Gamha Purnima","Odisha"),
    ))
    add([3,4],[17], _s("Kajari Teej","Madhya Pradesh","Uttar Pradesh","Bihar","Rajasthan","Chhattisgarh"))
    add([3,4],[22], _all("Krishna Janmashtami"))
    add([3,4],[23], _s("Nandotsav","Uttar Pradesh","Rajasthan","Madhya Pradesh"))
    add([3,4],[29], _s("Bail Pola / Pithori Amavasya","Maharashtra","Chhattisgarh","Madhya Pradesh"))

    # ── Bhadrapada festivals (Sun Leo/Virgo) ──────────────────────────────────
    add([4,5],[2], _s("Hartalika Teej","Maharashtra","Goa","Uttar Pradesh","Bihar","Rajasthan","Madhya Pradesh"))
    add([4,5],[3], _m(
        _all("Ganesh Chaturthi"),
        _s("Vinayaka Chaturthi (State Holiday)","Maharashtra","Goa","Karnataka",
           "Andhra Pradesh","Telangana","Tamil Nadu","Puducherry"),
    ))
    add([4,5],[4], _s("Rishi Panchami","Maharashtra","Gujarat","Rajasthan","Uttar Pradesh","Bihar","Madhya Pradesh"))
    add([4,5],[5], _s("Surya Shashti / Skanda Sashti","Tamil Nadu","Puducherry","Karnataka"))
    add([4,5],[7], _m(_all("Radha Ashtami"), _s("Gowri Habba","Karnataka")))
    add([4,5],[8], _s("Mahalakshmi Puja (3-day)","Maharashtra","Goa"))
    add([4,5],[10], _s("Khudurukuni Osha","Odisha"))
    add([4,5],[11,12], _s("Onam - Thiruvonam (Main Day)","Kerala","Lakshadweep"))
    add([4,5],[13], _m(_all("Anant Chaturdashi"), _s("Ganesh Visarjan (State Holiday)","Maharashtra","Goa")))
    add([4,5],[29], _m(
        _all("Mahalaya Amavasya / Pitru Paksha ends"),
        _s("Mahalaya / Durga Puja begins","West Bengal","Assam","Odisha","Tripura"),
    ))

    # ── Ashwin festivals (Sun Virgo/Libra) ────────────────────────────────────
    add([5,6],[0], _all("Shardiya Navratri begins / Ghatasthapana"))
    add([5,6],[3], _s("Karva Chauth","Rajasthan","Uttar Pradesh","Punjab","Haryana","Delhi",
                      "Himachal Pradesh","Madhya Pradesh","Uttarakhand","Bihar","Jammu & Kashmir","Chandigarh"))
    add([5,6],[5], _m(
        _s("Saraswati Puja / Saraswati Avahan","West Bengal","Odisha","Assam","Tripura","Bihar","Jharkhand"),
        _s("Ayudha Puja","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala","Puducherry"),
        _s("Lalita Sashti","Maharashtra","Gujarat"),
    ))
    add([5,6],[6], _s("Saraswati Puja (main day)","West Bengal","Odisha","Assam","Tripura"))
    add([5,6],[7], _m(_all("Durga Ashtami / Maha Ashtami"), _s("Sandhi Puja","West Bengal","Assam","Tripura")))
    add([5,6],[8], _m(
        _all("Maha Navami"),
        _s("Ayudha Puja (State Holiday)","Karnataka","Tamil Nadu","Andhra Pradesh","Telangana","Kerala","Puducherry"),
    ))
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

    # ── Kartik festivals (Sun Libra/Scorpio) ──────────────────────────────────
    add([6,7],[7], _s("Ahoi Ashtami","Uttar Pradesh","Rajasthan","Haryana","Punjab","Delhi","Madhya Pradesh","Himachal Pradesh"))
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
    add([6,7],[25], _m(_all("Dev Uthani Ekadashi / Tulsi Vivah"), _s("Kartik Ekadashi / Wari","Maharashtra","Goa")))
    add([6,7],[14], _m(
        _all("Kartik Purnima / Dev Deepawali"),
        _s("Guru Nanak Jayanti","Punjab","Haryana","Delhi","Himachal Pradesh","Uttarakhand","Chandigarh","Jammu & Kashmir"),
        _s("Pushkar Fair","Rajasthan"),
        _s("Tripuri Purnima","Tripura"),
        _s("Dev Deepawali (Varanasi)","Uttar Pradesh","Bihar","Uttarakhand"),
    ))

    # ── Margashirsha festivals (Sun Scorpio/Sagittarius) ──────────────────────
    add([7,8],[0], _s("Champa Shashthi / Khandoba Festival begins","Maharashtra","Goa"))
    add([7,8],[4], _s("Vivah Panchami","Uttar Pradesh","Bihar","Madhya Pradesh","Rajasthan","Uttarakhand","Delhi"))
    add([7,8],[5], _s("Champa Shashthi / Khandoba Festival (main day)","Maharashtra","Goa"))
    add([7,8],[10], _all("Mokshada Ekadashi / Gita Jayanti"))
    add([7,8],[14], _s("Dattatreya Jayanti","Maharashtra","Karnataka","Goa","Andhra Pradesh","Telangana","Gujarat"))

    # ── Paush festivals (Sun Sagittarius/Capricorn) ───────────────────────────
    add([8,9],[14], _m(
        _all("Paush Purnima"),
        _s("Shakambhari Purnima","Rajasthan","Uttar Pradesh","Madhya Pradesh"),
        _s("Gangasagar Mela","West Bengal"),
    ))

    # ── Magha festivals (Sun Capricorn/Aquarius) ──────────────────────────────
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
    add([9,10],[27,28], _all("Maha Shivratri"))

    # ── Phalguna festivals (Sun Aquarius/Pisces) ──────────────────────────────
    add([10,11],[4], _s("Rang Panchami","Maharashtra","Madhya Pradesh","Rajasthan","Gujarat","Chhattisgarh"))
    add([10,11],[9], _all("Amalaki Ekadashi"))
    add([10,11],[13], _m(_all("Holika Dahan"), _s("Shimga (Holi eve)","Maharashtra","Goa")))
    add([10,11],[14], _m(
        _all("Holi"),
        _s("Dol Jatra / Dol Purnima","West Bengal","Odisha","Assam","Tripura"),
        _s("Shigmo","Goa"),
        _s("Yaosang","Manipur"),
        _s("Phakuwa","Assam"),
    ))
    add([10,11],[15], _s("Dhuleti / Rangwali Holi","Gujarat","Rajasthan","Madhya Pradesh","Uttar Pradesh","Bihar","Chhattisgarh"))

    # Merge — later entries override earlier for same key
    result = {}
    for key, sd in entries:
        if key not in result:
            result[key] = {}
        result[key].update(sd)
    return result

LUNAR_RULES = _build_lunar_rules()

# ═════════════════════════════════════════════════════════════════════════════
# SOLAR RULES — fixed by solar/Gregorian calendar
# Built as a function to avoid duplicate key bugs
# ═════════════════════════════════════════════════════════════════════════════

def _build_solar_rules():
    entries = [
        # National
        ((1,  1), _all("New Year's Day")),
        ((1, 12), _s("Swami Vivekananda Jayanti","West Bengal","Assam","Odisha","Tripura","Andaman & Nicobar")),
        ((1, 23), _s("Netaji Subhash Chandra Bose Jayanti","West Bengal","Odisha","Assam","Tripura")),
        ((1, 26), _all("Republic Day")),
        ((2, 19), _s("Chhatrapati Shivaji Maharaj Jayanti","Maharashtra","Goa","Dadra & Nagar Haveli")),
        ((3, 23), _s("Shaheed Diwas (Bhagat Singh)","Punjab","Haryana","Delhi","Chandigarh","Uttar Pradesh")),
        ((4, 14), _all("Dr. Ambedkar Jayanti")),
        ((5,  1), _all("International Labour Day")),
        ((8, 15), _all("Independence Day")),
        ((9,  5), _all("Teachers Day")),
        ((10, 2), _all("Gandhi Jayanti")),
        ((12,25), _all("Christmas")),
        # Makar Sankranti — solar, genuinely fixed
        ((1, 13), _s("Bhogi Pongal","Tamil Nadu","Puducherry","Andhra Pradesh","Telangana")),
        ((1, 14), _m(
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
        ((1, 15), _m(_s("Thiruvalluvar Day","Tamil Nadu","Puducherry"), _s("Magh Bihu (State Holiday)","Assam"))),
        ((1, 16), _s("Mattu Pongal / Uzhavar Thirunal","Tamil Nadu","Puducherry")),
        ((1, 17), _s("Kannum Pongal","Tamil Nadu","Puducherry")),
        ((1, 18), _m(_s("Jallikattu","Tamil Nadu"), _s("Lui-Ngai-Ni (Naga New Year)","Nagaland","Manipur"))),
        ((1, 31), _s("Me-Dam-Me-Phi (Ahom)","Assam")),
        # February
        ((2,  1), _m(_s("Surajkund Craft Mela","Haryana","Delhi"), _s("Kala Ghoda Arts Festival (Mumbai)","Maharashtra"))),
        # March
        ((3,  1), _s("Chapchar Kut (State Holiday)","Mizoram")),
        ((3, 18), _s("Gangaur","Rajasthan","Madhya Pradesh","Gujarat")),
        ((3, 22), _s("Bihar Diwas","Bihar","Jharkhand")),
        ((3, 28), _s("Karaga Festival (Bangalore)","Karnataka")),
        ((3, 30), _s("Rajasthan Day","Rajasthan")),
        # April
        ((4,  1), _m(_s("Utkal Diwas (Odisha Foundation Day)","Odisha"), _s("Vairamudi Festival (Melkote)","Karnataka"))),
        ((4, 10), _s("Thrissur Pooram","Kerala")),
        ((4, 13), _m(_s("Bohag Bihu / Rongali Bihu (State Holiday)","Assam"), _s("Sajibu Cheiraoba (Meitei New Year)","Manipur"))),
        ((4, 14), _m(
            _s("Baisakhi / Vaisakhi","Punjab","Haryana","Himachal Pradesh","Delhi","Chandigarh","Uttarakhand"),
            _s("Puthandu / Tamil New Year","Tamil Nadu","Puducherry"),
            _s("Vishu","Kerala","Lakshadweep"),
            _s("Pohela Boishakh / Bengali New Year","West Bengal","Tripura","Assam"),
            _s("Himachal Day","Himachal Pradesh"),
            _s("Pana Sankranti / Maha Vishuba Sankranti","Odisha"),
        )),
        ((4, 15), _m(_s("Himachal Pradesh Foundation Day","Himachal Pradesh"), _s("Pohela Boishakh (State Holiday)","West Bengal","Tripura"))),
        # May
        ((5,  1), _m(_s("Maharashtra Day","Maharashtra","Goa","Dadra & Nagar Haveli"), _s("Gujarat Day","Gujarat"))),
        ((5,  3), _s("Hampi Utsav / Vijayanagara Festival","Karnataka")),
        ((5,  9), _s("Rabindra Jayanti","West Bengal","Tripura","Assam")),
        ((5, 16), _s("Sikkim Statehood Day","Sikkim")),
        # June
        ((6,  1), _s("Telangana Formation Day","Telangana")),
        ((6, 13), _s("Feast of St Anthony","Goa")),
        ((6, 20), _m(_s("Ambubachi Mela (Kamakhya)","Assam"), _s("Raja Parba","Odisha"))),
        ((6, 24), _s("Sao Joao","Goa")),
        # July
        ((7, 17
), _s("Kharchi Puja (State Holiday)","Tripura")),
        # August
        ((8,  9), _s("Karma Puja","Jharkhand","Odisha","Chhattisgarh","West Bengal")),
        ((8, 15), _s("Feast of Assumption of Our Lady","Goa")),
        ((8, 20), _s("Nuakhai (State Holiday)","Odisha","Chhattisgarh")),
        ((8, 26), _s("Ker Puja","Tripura")),
        # September
        ((9,  1), _m(_s("Bathukamma begins","Telangana"), _s("Sree Narayana Guru Samadhi","Kerala"), _s("Ladakh Festival","Ladakh"))),
        ((9, 18), _s("Pola / Bail Pola","Maharashtra","Chhattisgarh","Madhya Pradesh")),
        ((9, 20), _s("Mim Kut","Mizoram")),
        ((9, 22), _s("Pang Lhabsol","Sikkim")),
        # October
        ((10, 2), _m(_s("Bathukamma (main day)","Telangana"), _s("Kullu Dussehra begins","Himachal Pradesh"))),
        ((10,14), _s("Tula Sankramana (Talakaveri)","Karnataka")),
        ((10,15), _s("Pushkar Camel Fair","Rajasthan")),
        ((10,18), _s("Kongali Bihu / Kati Bihu","Assam")),
        ((10,24), _s("J&K Accession Day","Jammu & Kashmir","Ladakh")),
        # November
        ((11, 1), _m(
            _s("Karnataka Rajyotsava (State Holiday)","Karnataka"),
            _s("Haryana Day","Haryana","Chandigarh"),
            _s("Punjab Day","Punjab","Chandigarh"),
            _s("MP Foundation Day","Madhya Pradesh","Chhattisgarh"),
            _s("Kerala Piravi","Kerala","Lakshadweep"),
            _s("Chavang Kut (Kuki-Zo)","Manipur"),
        )),
        ((11, 6), _s("Kambala (Buffalo Race) season begins","Karnataka")),
        ((11, 9), _s("Uttarakhand Foundation Day","Uttarakhand")),
        ((11,15), _m(_s("Jharkhand Foundation Day","Jharkhand"), _s("Birsa Munda Jayanti","Jharkhand","Odisha","West Bengal","Chhattisgarh"))),
        ((11,19), _s("Hornbill Festival begins","Nagaland")),
        ((11,28), _s("Ningol Chakouba","Manipur")),
        # December
        ((12, 1), _m(_s("Nagaland Statehood Day / Hornbill Festival","Nagaland"), _s("International Sand Art Festival (Puri)","Odisha"))),
        ((12, 2), _s("Mizoram Statehood Day","Mizoram")),
        ((12, 3), _s("Feast of St Francis Xavier","Goa")),
        ((12, 8), _s("Feast of Immaculate Conception","Goa")),
        ((12,19), _s("Goa Liberation Day","Goa","Dadra & Nagar Haveli")),
        ((12,22), _s("Pattadakal Dance Festival","Karnataka")),
        ((12,27), _s("Losoong / Namsoong (Sikkimese New Year)","Sikkim")),
        ((12,31), _s("Pawl Kut","Mizoram")),
        # Maharashtra specific
        ((1,  6), _s("Feast of Three Kings (Christians)","Goa","Maharashtra")),
        ((2, 20), _s("Goa Carnival","Goa")),
        ((3, 15), _s("Ellora-Ajanta Festival","Maharashtra")),
        # Kerala specific
        ((2, 15), _s("Attukal Pongala (Thiruvananthapuram)","Kerala")),
        ((8, 10), _s("Nehru Trophy Boat Race (Alappuzha)","Kerala")),
        ((8, 29), _s("Onam / Thiruvonam (State Holiday)","Kerala","Lakshadweep")),
        ((11, 5), _s("Aranmula Boat Race","Kerala")),
        # Arunachal Pradesh tribal
        ((1,  5), _s("Losar (Monpa New Year)","Arunachal Pradesh","Sikkim","Ladakh")),
        ((2, 26), _s("Nyokum Yullo (Nishi tribe)","Arunachal Pradesh")),
        ((4,  5), _s("Mopin (Adi tribe)","Arunachal Pradesh")),
        ((4,  1), _s("Ali-Aye Ligang (Mishing tribe)","Arunachal Pradesh","Assam")),
        ((7,  5), _s("Dree Festival (Apatani tribe)","Arunachal Pradesh")),
        ((9,  5), _s("Solung (Adi tribe)","Arunachal Pradesh")),
        # Nagaland tribal
        ((5,  1), _s("Moatsu (Ao Naga)","Nagaland")),
        ((8, 10), _s("Sekrenyi (Angami Naga)","Nagaland")),
        # Rajasthan
        ((2,  1), _s("Bikaner Camel Festival","Rajasthan")),
        # Uttarakhand
        ((3, 22), _s("Phool Dei (Spring Festival)","Uttarakhand")),
        ((7, 15), _s("Harela (Kumaon harvest)","Uttarakhand")),
        # J&K
        ((6, 15), _s("Hemis Festival","Ladakh","Jammu & Kashmir")),
        # Puducherry
        ((8, 15), _s("Puducherry De Facto Transfer Day","Puducherry")),
        ((11, 1), _s("Puducherry Liberation Day","Puducherry")),
        # Andaman
        ((3,  4), _s("Island Tourism Festival","Andaman & Nicobar")),
        ((1, 12), _s("Swami Vivekananda Jayanti","Andaman & Nicobar")),
    ]
    result = {}
    for key, sd in entries:
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
        "moon_elongation": diff,
    }


def _collect_state_festivals(p: dict, d) -> dict:
    state_map = {s: [] for s in ALL_STATES}

    def _apply(rule_dict, key):
        entry = rule_dict.get(key)
        if not entry:
            return
        for state, name in entry.items():
            if name and state in state_map and name not in state_map[state]:
                state_map[state].append(name)

    _apply(LUNAR_RULES, (p["sun_sign_index"], p["tithi_index"]))

    # Nakshatra override: Onam Thiruvonam = Shravana nakshatra in Bhadrapada
    if p["sun_sign_index"] in [4, 5] and p["nakshatra_index"] == 21:
        for s in ["Kerala", "Lakshadweep"]:
            if "Onam - Thiruvonam (Main Day)" not in state_map[s]:
                state_map[s].insert(0, "Onam - Thiruvonam (Main Day)")

    _apply(SOLAR_RULES, (d.month, d.day))

    india_hols = holidays_lib.India(years=d.year)
    official   = india_hols.get(d)
    if official:
        for s in ALL_STATES:
            if official not in state_map[s]:
                state_map[s].append(official)

    return state_map


def _crop_demand_signal(tithi_index: int, festivals: list, vara_index: int) -> dict:
    """
    Returns demand signal features for crop price ML model.
    Higher score = higher expected market demand.
    """
    is_amavasya  = tithi_index == 29
    is_purnima   = tithi_index == 14
    is_ekadashi  = tithi_index in [10, 25]
    is_chaturdashi = tithi_index in [13, 28]
    is_shukla    = tithi_index < 15
    festival_count = len(festivals)

    # Demand score 0-10
    score = 0
    if is_purnima:   score += 3   # high demand — Purnima markets
    if is_amavasya:  score += 2   # moderate — Amavasya rituals
    if is_ekadashi:  score += 1   # fasting day — reduced vegetable demand
    if festival_count >= 3: score += 3
    elif festival_count >= 1: score += 2
    if vara_index == 6:  score += 1  # Sunday market
    if vara_index == 0:  score += 1  # Monday market (Somavar)

    # Fasting flag — affects vegetable/fruit demand
    is_fasting_day = is_ekadashi or is_chaturdashi or is_amavasya

    # Flower demand spike
    flower_demand = is_purnima or is_amavasya or festival_count >= 2

    return {
        "demand_score":    min(score, 10),
        "is_amavasya":     is_amavasya,
        "is_purnima":      is_purnima,
        "is_ekadashi":     is_ekadashi,
        "is_fasting_day":  is_fasting_day,
        "is_festival_day": festival_count > 0,
        "festival_count":  festival_count,
        "flower_demand_high": flower_demand,
        "is_shukla_paksha": is_shukla,
    }


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

def get_calendar_data(date_str: str, state: str = None) -> dict:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    p = _compute_panchang(d.year, d.month, d.day)

    tithi_name       = f"{PAKSHA[p['tithi_index']]} {TITHI_NAMES[p['tithi_index']]}"
    nakshatra_name   = NAKSHATRAS[p["nakshatra_index"]]
    yoga_name        = YOGA_NAMES[p["yoga_index"]]
    karana_name      = KARANA_NAMES[p["karana_index"]]
    vara_name        = VARA_NAMES[p["vara_index"]]
    lunar_month_name = LUNAR_MONTH_NAMES[p["sun_sign_index"]]

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

    ti = p["tithi_index"]

    return {
        "date":        date_str,
        "tithi":       tithi_name,
        "nakshatra":   nakshatra_name,
        "is_amavasya": ti == 29,
        "is_purnima":  ti == 14,
        "is_ekadashi": ti in [10, 25],
        "festivals":   all_unique,
        "state_festivals": active,
    }
