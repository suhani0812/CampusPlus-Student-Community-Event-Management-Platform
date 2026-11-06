import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host     = os.getenv("DB_HOST", "localhost"),
    dbname   = os.getenv("DB_NAME", "campusplus"),
    user     = os.getenv("DB_USER", "postgres"),
    password = os.getenv("DB_PASSWORD", ""),
    port     = os.getenv("DB_PORT", "5432"),
)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM accommodations")
count = cur.fetchone()[0]

if count == 0:
    properties = [
        {
            "listed_by": 1,
            "type": "pg",
            "title": "Stanza Living Munich House — Luxury Student PG",
            "address": "Survey No. 128, Near MIT-WPU Back Gate, Paud Road, Kothrud, Pune - 411038",
            "location_url": "https://maps.google.com/?q=Stanza+Living+Munich+House+Pune",
            "rent": 12500.00,
            "broker_name": "Rajesh Sharma (Property Mgr)",
            "broker_contact": "+91 98230 45671",
            "status": "approved",
            "images": [
                "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=1000&q=80"
            ],
            "reviews": [
                (2, 5, "Extremely clean rooms, 350 Mbps WiFi, and food is actually hygienic. 4 minutes walking distance from campus gate!"),
                (1, 4, "Great amenities like biometric access and daily housekeeping. Rent is slightly on the higher side but worth the safety.")
            ]
        },
        {
            "listed_by": 2,
            "type": "pg",
            "title": "Oxford Girls Executive PG — AC & Food Included",
            "address": "Plot 42, Ideal Colony, Near Joggers Park, Kothrud, Pune - 411038",
            "location_url": "https://maps.google.com/?q=Ideal+Colony+Kothrud+Pune",
            "rent": 9500.00,
            "broker_name": "Mrs. Sunita Deshmukh",
            "broker_contact": "+91 94220 18923",
            "status": "approved",
            "images": [
                "https://images.unsplash.com/photo-1540518614846-7ede433c4ef3?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1000&q=80"
            ],
            "reviews": [
                (1, 5, "Safe gated society for female students. CCTV on all floors, healthy home-cooked Maharashtrian & North Indian food.")
            ]
        },
        {
            "listed_by": 1,
            "type": "hostel",
            "title": "Campus View Boys International Hostel",
            "address": "Lane 3, Opposite MIT School of Design, Rambaug Colony, Kothrud, Pune",
            "location_url": "https://maps.google.com/?q=Rambaug+Colony+Kothrud+Pune",
            "rent": 7800.00,
            "broker_name": "Kailash Patil (Warden)",
            "broker_contact": "+91 97654 32109",
            "status": "approved",
            "images": [
                "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1000&q=80"
            ],
            "reviews": [
                (2, 4, "Budget friendly option right across the street. Huge reading room and solar water heating. Recommended for engineering juniors.")
            ]
        },
        {
            "listed_by": 2,
            "type": "flat",
            "title": "Fully Furnished 2BHK Apartment for 4 Students",
            "address": "B-402, Mayur Heights, Mayur Colony, Kothrud, Pune - 411038",
            "location_url": "https://maps.google.com/?q=Mayur+Colony+Kothrud+Pune",
            "rent": 28000.00,
            "broker_name": "Direct Owner — Amit Joshi",
            "broker_contact": "+91 98901 23456",
            "status": "approved",
            "images": [
                "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=1000&q=80"
            ],
            "reviews": [
                (1, 5, "Split among 4 students it comes to ₹7,000 each! Comes with fridge, washing machine, modular kitchen, and zero brokerage.")
            ]
        },
        {
            "listed_by": 1,
            "type": "pg",
            "title": "Zolo Stays Paud Road — Premium Co-living",
            "address": "Paud Road, Landmark: Near Vanaz Metro Station, Kothrud, Pune",
            "location_url": "https://maps.google.com/?q=Vanaz+Metro+Station+Pune",
            "rent": 14000.00,
            "broker_name": "Zolo Community Manager",
            "broker_contact": "+91 88801 08010",
            "status": "approved",
            "images": [
                "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?auto=format&fit=crop&w=1000&q=80",
                "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?auto=format&fit=crop&w=1000&q=80"
            ],
            "reviews": [
                (2, 4, "Close to Vanaz metro. Gaming lounge, gym, and rooftop study terrace. Good crowd of MIT-WPU students.")
            ]
        },
        {
            "listed_by": 2,
            "type": "hostel",
            "title": "Shree Ram Student Residency (Single & Double Sharing)",
            "address": "Behind Karve Statue, Karve Road, Kothrud, Pune - 411038",
            "location_url": "https://maps.google.com/?q=Karve+Road+Kothrud+Pune",
            "rent": 6500.00,
            "broker_name": "Suresh Shinde",
            "broker_contact": "+91 93710 44556",
            "status": "approved",
            "images": [
                "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?auto=format&fit=crop&w=1000&q=80"
            ],
            "reviews": [
                (1, 4, "Most economical stay near campus. Power backup, water purifier, and strict night security.")
            ]
        }
    ]

    for p in properties:
        cur.execute("""
            INSERT INTO accommodations 
                (listed_by, type, title, address, location_url, rent, broker_name, broker_contact, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            p["listed_by"], p["type"], p["title"], p["address"], p["location_url"],
            p["rent"], p["broker_name"], p["broker_contact"], p["status"]
        ))
        acc_id = cur.fetchone()[0]

        for img in p["images"]:
            cur.execute("""
                INSERT INTO accommodation_images (accommodation_id, image_url)
                VALUES (%s, %s)
            """, (acc_id, img))

        for rev in p["reviews"]:
            cur.execute("""
                INSERT INTO accommodation_reviews (accommodation_id, reviewed_by, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, (acc_id, rev[0], rev[1], rev[2]))

    conn.commit()
    print("Seeded 6 accommodations with images & reviews successfully!")
else:
    print(f"Accommodations already has {count} rows.")

cur.close()
conn.close()
