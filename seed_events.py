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

cur.execute("SELECT COUNT(*) FROM events")
count = cur.fetchone()[0]

if count == 0:
    events = [
        (
            6, 1, "HACK MIT 2026: 36-Hour National Flagship Hackathon",
            "MIT-WPU’s premier annual hackathon bringing together over 500 developers across India to build solutions in AI, Web3, FinTech, and Smart Healthcare with ₹5,00,000 in cash prizes.",
            "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80",
            "academic", "on_campus", "Dr. Vishwanath Karad Hall, Building 3",
            "2026-11-14 09:00:00", "2026-11-15 21:00:00",
            "https://hackmit.mitwpu.edu.in", "approved"
        ),
        (
            1, 1, "Aarohan 2026: Annual Inter-College Cultural Extravaganza",
            "The biggest college festival in Pune featuring live band performances, street plays (Nukkad Natak), celebrity DJ nights, fashion walks, and dance battles.",
            "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1200&q=80",
            "social", "on_campus", "MIT-WPU Main Open Amphitheatre",
            "2026-11-20 17:00:00", "2026-11-22 22:30:00",
            "https://aarohan.mitwpu.edu.in/register", "approved"
        ),
        (
            3, 1, "Cloud & GenAI Developer Summit 2026",
            "Hands-on workshops on AWS Bedrock, Kubernetes container orchestration, and deploying LLM microservices with industry experts from Google Cloud and Microsoft.",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80",
            "academic", "on_campus", "Auditorium 2, School of Engineering",
            "2026-11-08 10:00:00", "2026-11-08 17:00:00",
            "https://initcloud.mitwpu.edu.in/summit", "approved"
        ),
        (
            8, 1, "Night Under The Stars: Telescopic Deep Space Stargazing",
            "Observe Jupiter’s moons, Saturn’s rings, and the Orion Nebula through automated 8-inch Dobsonian telescopes guided by astrophysicists.",
            "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=1200&q=80",
            "social", "off_campus", "Sinhagad Fort Astronomical Point, Pune",
            "2026-11-28 19:30:00", "2026-11-29 05:30:00",
            "https://cosmos.mitwpu.edu.in/stargazing", "approved"
        ),
        (
            4, 1, "Women in Tech & Leadership Conclave 2026",
            "Keynotes, panel discussions, and resume clinics led by women engineering leaders from top tech firms, focusing on career breakthroughs and mentorship.",
            "https://images.unsplash.com/photo-1573164713988-8665fc963095?auto=format&fit=crop&w=1200&q=80",
            "academic", "on_campus", "Sant Dnyaneshwar World Peace Hall",
            "2026-11-18 11:00:00", "2026-11-18 16:30:00",
            "https://acm-w.mitwpu.edu.in/conclave", "approved"
        ),
        (
            2, 1, "Fort Rajmachi Winter Trek & Eco-Cleanup Drive",
            "Two-day scenic trek through the Sahyadris partnered with Giripremi Foundation. Includes camping, survival skills training, and an environmental cleanup drive.",
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
            "social", "off_campus", "Rajmachi Plateau, Lonavala",
            "2026-12-05 06:00:00", "2026-12-06 18:00:00",
            "https://nisargvedh.mitwpu.edu.in/rajmachi", "approved"
        )
    ]

    for ev in events:
        cur.execute("""
            INSERT INTO events 
                (club_id, created_by, title, description, poster_url, type, location_type, venue, event_date, end_date, registration_link, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ev)
    conn.commit()
    print("Seeded 6 sample events successfully!")
else:
    print(f"Events table already has {count} rows.")

cur.close()
conn.close()
