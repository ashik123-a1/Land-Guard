"""Generates synthetic, fictional owners and land parcels for LandGuard."""

import random
import uuid
from typing import List, Dict, Any, Tuple

FIRST_NAMES = [
    ("Mohammad", "মোহাম্মদ"), ("Abdur", "আব্দুর"), ("Abdul", "আব্দুল"),
    ("Fatema", "ফাতেমা"), ("Rokeya", "রোকেয়া"), ("Jahanara", "জাহানারা"),
    ("Nazrul", "নজরুল"), ("Kamal", "কামাল"), ("Rashid", "রশীদ"),
    ("Anowar", "আনোয়ার"), ("Farida", "ফরিদা"), ("Tahmina", "তাহমিনা"),
    ("Kazi", "কাজী"), ("Syed", "সৈয়দ"), ("Nasreen", "নাসরীন"),
    ("Shamsur", "শামসুর"), ("Habibur", "হাবিবুর"), ("Zillur", "জিল্লুর"),
    ("Monir", "মনির"), ("Mahmud", "মাহমুদ"), ("Sultana", "সুলতানা")
]

LAST_NAMES = [
    ("Rahman", "রহমান"), ("Hossain", "হোসেন"), ("Ahmed", "আহমেদ"),
    ("Chowdhury", "চৌধুরী"), ("Khan", "খান"), ("Haque", "হক"),
    ("Ali", "আলী"), ("Islam", "ইসলাম"), ("Sikder", "শিকদার"),
    ("Miah", "মিয়া"), ("Akter", "আক্তার"), ("Begum", "বেগম"),
    ("Talukder", "তালুকদার"), ("Bhuiyan", "ভূঁইয়া"), ("Majumder", "মজুমদার")
]

LOCATIONS = [
    {"district": "Dhaka", "upazila": "Savar", "mouza": "Bagbari", "jl": 142},
    {"district": "Dhaka", "upazila": "Dhamrai", "mouza": "Kushura", "jl": 89},
    {"district": "Dhaka", "upazila": "Keraniganj", "mouza": "Ruhitpur", "jl": 55},
    {"district": "Chattogram", "upazila": "Sitakunda", "mouza": "Barabkunda", "jl": 112},
    {"district": "Chattogram", "upazila": "Hathazari", "mouza": "Fatehabad", "jl": 76},
    {"district": "Sylhet", "upazila": "Beanibazar", "mouza": "Kurarbazar", "jl": 94},
    {"district": "Rajshahi", "upazila": "Paba", "mouza": "Harigram", "jl": 63},
    {"district": "Khulna", "upazila": "Rupsha", "mouza": "Naihati", "jl": 48}
]

LAND_CLASSES = ["Viti", "Nal", "Bari", "Pukur", "Chala", "Dokan"]


def generate_owner(rng: random.Random) -> Dict[str, Any]:
    first_en, first_bn = rng.choice(FIRST_NAMES)
    last_en, last_bn = rng.choice(LAST_NAMES)
    father_first, _ = rng.choice(FIRST_NAMES)
    father_last, _ = rng.choice(LAST_NAMES)
    
    loc = rng.choice(LOCATIONS)
    uid = uuid.UUID(int=rng.getrandbits(128)).hex[:8].upper()
    nid_digits = "".join(str(rng.randint(0, 9)) for _ in range(10))
    
    return {
        "owner_id": f"OWN-{uid}",
        "full_name_en": f"{first_en} {last_en}",
        "full_name_bn": f"{first_bn} {last_bn}",
        "fictional_nid": f"SYN-{nid_digits}",
        "father_or_spouse_name": f"Late {father_first} {father_last}",
        "fictional_address": f"Village: {loc['mouza']}, Post: {loc['upazila']}, District: {loc['district']}",
        "district": loc["district"],
        "upazila": loc["upazila"],
        "mouza": loc["mouza"],
        "is_synthetic": True
    }


def generate_parcel(rng: random.Random, loc: Dict[str, Any] = None) -> Dict[str, Any]:
    if loc is None:
        loc = rng.choice(LOCATIONS)
    
    uid = uuid.UUID(int=rng.getrandbits(128)).hex[:8].upper()
    dag_no = rng.randint(101, 9999)
    area = round(rng.uniform(3.5, 95.0), 2)
    lclass = rng.choice(LAND_CLASSES)
    
    # Simple polygon coords for maps
    w = rng.uniform(40, 100)
    h = rng.uniform(40, 100)
    poly = [[0, 0], [w, rng.uniform(-5, 5)], [w + rng.uniform(-5, 5), h], [rng.uniform(-5, 5), h]]
    
    return {
        "parcel_id": f"PAR-{uid}",
        "district": loc["district"],
        "upazila": loc["upazila"],
        "mouza": loc["mouza"],
        "jl_number": loc["jl"],
        "dag_plot_number": dag_no,
        "total_area_decimal": area,
        "land_classification": lclass,
        "boundaries": {
            "north": f"Plot #{dag_no - 1}",
            "south": f"Plot #{dag_no + 1}",
            "east": f"Road / Plot #{dag_no + 5}",
            "west": f"Canal / Plot #{dag_no - 4}"
        },
        "coordinates_relative": poly,
        "is_synthetic": True
    }


def generate_entities(count_owners: int, count_parcels: int, seed: int = 42) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rng = random.Random(seed)
    owners = [generate_owner(rng) for _ in range(count_owners)]
    parcels = [generate_parcel(rng) for _ in range(count_parcels)]
    return owners, parcels
