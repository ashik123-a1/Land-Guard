"""Tests JSON Schema compliance for all synthetic entities."""

import json
import pytest
from src.landguard_data.validate_dataset import load_schema, validate_schema
from src.landguard_data.generate_entities import generate_owner, generate_parcel
import random


def test_owner_schema():
    rng = random.Random(42)
    owner = generate_owner(rng)
    schema = load_schema("schemas/owner.schema.json")
    is_valid, err = validate_schema(owner, schema)
    assert is_valid, f"Owner schema validation failed: {err}"


def test_parcel_schema():
    rng = random.Random(42)
    parcel = generate_parcel(rng)
    schema = load_schema("schemas/parcel.schema.json")
    is_valid, err = validate_schema(parcel, schema)
    assert is_valid, f"Parcel schema validation failed: {err}"
