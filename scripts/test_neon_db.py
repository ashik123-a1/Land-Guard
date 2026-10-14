import psycopg2
import hashlib

DATABASE_URL = "postgresql://neondb_owner:npg_AJQWk1lwH0Im@ep-falling-hat-b4bi5i99-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Seed Roles
roles = [
    ("CITIZEN", "Verified Citizen User", "Citizen holding digital land identity card and verified parcels."),
    ("INVESTIGATOR", "Land Fraud Investigator", "Authorized investigator reviewing statutory deeds and double sales."),
    ("ADMIN", "System Administrator", "Platform administrator managing governance, rulesets, and SLAs."),
]
for role_id, name, desc in roles:
    cur.execute(
        """
        INSERT INTO roles (role_id, role_name, description)
        VALUES (%s, %s, %s)
        ON CONFLICT (role_id) DO UPDATE SET role_name = EXCLUDED.role_name, description = EXCLUDED.description;
        """,
        (role_id, name, desc),
    )

# Seed Users
users = [
    (
        "USR-CITIZEN-001",
        "citizen@landguard.gov.bd",
        hashlib.sha256("demo123".encode()).hexdigest(),
        "Rafiqul Islam",
        "CITIZEN",
        "19882691234567890",
        "CIT-BD-884920",
        "+880 1712-345678",
        "Dhaka",
        "Dhaka",
        "Savar",
    ),
    (
        "USR-INVESTIGATOR-001",
        "investigator@landguard.gov.bd",
        hashlib.sha256("demo123".encode()).hexdigest(),
        "Inspector S. Karim",
        "INVESTIGATOR",
        "19822699876543210",
        "OFF-INV-2041",
        "+880 1819-223344",
        "Dhaka",
        "Dhaka",
        "Motijheel",
    ),
    (
        "USR-ADMIN-001",
        "admin@landguard.gov.bd",
        hashlib.sha256("admin123".encode()).hexdigest(),
        "Super Administrator",
        "ADMIN",
        "19752690001122334",
        "ADM-HQ-001",
        "+880 1911-001122",
        "Dhaka",
        "Dhaka",
        "Secretariat",
    ),
]

for uid, email, phash, name, role, nid, dig_id, phone, div, dist, upz in users:
    cur.execute(
        """
        INSERT INTO users (user_id, email, password_hash, full_name, role, national_id, digital_identity_id, phone, division, district, upazila)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET email = EXCLUDED.email, full_name = EXCLUDED.full_name;
        """,
        (uid, email, phash, name, role, nid, dig_id, phone, div, dist, upz),
    )

conn.commit()
print("Roles and Users seeded successfully in Neon DB!")

cur.execute("SELECT user_id, email, role, full_name FROM users;")
print("Users in Neon:", cur.fetchall())

cur.close()
conn.close()
