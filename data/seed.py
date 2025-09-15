# data/seed.py
"""
Seed-Skript für Topics & Skills.
- Läuft ohne create_app(): importiert direkt 'app' aus app.py
- Idempotent: legt Einträge nur an, wenn sie noch nicht existieren
- Ausgabe zeigt erzeugte UUIDs zum manuellen Kopieren in Postman
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1) Pfad so erweitern, dass wir 'app.py' und 'models.py' aus dem Projektwurzelordner importieren können
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 2) Jetzt sind 'app.py' und 'models.py' importierbar
from app import app  # verwendet die bereits erstellte Flask-App (kein create_app nötig)
from models import db, Topic, Skill

load_dotenv()  # optional: liest DATABASE_URL aus .env, falls gesetzt

# 3) Beispiel-Daten
TOPICS = [
    ("Web Development Fundamentals", "Grundlagen für Webanwendungen"),
    ("Frontend Development", "UI bauen"),
    ("Backend Development", "Serverlogik & Datenbanken"),
    ("Data Analysis Basics", "Statistik & Visualisierung"),
    ("Databases 101", "SQL & Datenmodellierung"),
]

SKILLS = [
    # (name, topic_name, difficulty)
    ("HTML Basics", "Web Development Fundamentals", "beginner"),
    ("CSS Layouts (Flex/Grid)", "Web Development Fundamentals", "intermediate"),
    ("JavaScript ES6+", "Web Development Fundamentals", "intermediate"),
    ("React Hooks", "Frontend Development", "advanced"),
    ("APIs mit Flask", "Backend Development", "intermediate"),
    ("SQL SELECT Basics", "Databases 101", "beginner"),
    ("Joins & Aggregation", "Databases 101", "intermediate"),
    ("Explorative Analyse", "Data Analysis Basics", "beginner"),
]

def get_or_create_topic(name: str, desc: str) -> Topic:
    """Liefert Topic mit 'name' oder legt es neu an."""
    t = Topic.query.filter(Topic.name == name).first()
    if not t:
        t = Topic(name=name, description=desc)
        db.session.add(t)
        db.session.commit()
    return t

def get_or_create_skill(name: str, topic: Topic, diff: str) -> Skill:
    """Liefert Skill mit (name, topic_id) oder legt ihn neu an."""
    s = Skill.query.filter(
        Skill.name == name,
        Skill.topic_id == topic.id
    ).first()
    if not s:
        s = Skill(name=name, topic_id=topic.id, difficulty=diff)
        db.session.add(s)
        db.session.commit()
    return s

if __name__ == "__main__":
    # 4) Innerhalb eines App-Kontextes arbeiten (erforderlich für DB-Zugriffe)
    with app.app_context():
        # (Optional) Falls Migrationen nicht gelaufen sind, Tabellen anlegen:
        # Hinweis: In Produktions-Workflows nutzt man 'flask db upgrade'.
        try:
            # Prüfe, ob Tabellen existieren; wenn nicht, lege sie an:
            db.create_all()
        except Exception as e:
            print("Warnung: Konnte db.create_all() nicht ausführen:", e)

        print("Seeding topics...")
        topics_by_name = {}
        for n, d in TOPICS:
            t = get_or_create_topic(n, d)
            topics_by_name[n] = t
            print(f"  - {n}: {t.id}")

        print("Seeding skills...")
        for name, topic_name, diff in SKILLS:
            parent_topic = topics_by_name.get(topic_name)
            if not parent_topic:
                raise RuntimeError(f"Topic '{topic_name}' wurde nicht gefunden. Reihenfolge im TOPICS-Array prüfen.")
            s = get_or_create_skill(name, parent_topic, diff)
            print(f"  - {name} ({topic_name}, {diff}): {s.id}")

        print("\nFertig. Kopiere eine Topic-ID und eine Skill-ID für Postman-Tests.")
