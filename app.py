# app.py
# -*- coding: utf-8 -*-
"""
Topic & Skill Service (Flask + SQLAlchemy + PostgreSQL)

- Application Factory: create_app() erstellt/konfiguriert die Flask-App.
- Alle Routen sind innerhalb der Factory definiert.
- Features:
  - Healthcheck
  - Topics: CRUD, Suche (q), Parent-Filter (parentId), Pagination (limit/offset), Delete-Guard
  - Skills:  CRUD, Suche (q), Topic-Filter (topicId), Pagination (limit/offset)

Voraussetzungen:
- models.py definiert: db = SQLAlchemy(), sowie Modelle Topic und Skill mit .to_dict()
- PostgreSQL läuft; DATABASE_URL in .env oder Fallback-URL unten.
"""

import os
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from dotenv import load_dotenv
from sqlalchemy import exists
from models import db, Topic, Skill

# .env (optional) laden, z. B. für DATABASE_URL
load_dotenv()


def create_app() -> Flask:
    """
    Application Factory.
    Erstellt die Flask-App, konfiguriert die Datenbank und registriert alle Routen.
    """
    app = Flask(__name__)

    # -------------------------------------------------------------------------
    # DB-Konfiguration
    # -------------------------------------------------------------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://app:app123@localhost:5432/topics_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # SQLAlchemy und Migrationen initialisieren
    db.init_app(app)
    Migrate(app, db)

    # -------------------------------------------------------------------------
    # Basis/Health
    # -------------------------------------------------------------------------
    @app.get("/")
    def root():
        """Einfacher Begrüßungs-Endpoint (schneller manueller Test)."""
        return "Hello from Topic & Skill Service!"

    @app.get("/healthz")
    def healthz():
        """Liveness/Readiness Check."""
        return {"status": "ok"}

    # -------------------------------------------------------------------------
    # Topics: CRUD + Suche/Filter/Pagination + Delete-Guard
    # -------------------------------------------------------------------------
    @app.get("/topics")
    def list_topics():
        """
        Liste aller Topics (mit optionaler Suche/Filterung und Pagination).
        """
        q = request.args.get("q")
        parent_id = request.args.get("parentId")

        limit = min(int(request.args.get("limit", 50)), 200)
        offset = max(int(request.args.get("offset", 0)), 0)

        query = Topic.query
        if q:
            query = query.filter(Topic.name.ilike(f"%{q}%"))
        if parent_id:
            query = query.filter(Topic.parent_topic_id == parent_id)

        total = query.count()
        items = (
            query.order_by(Topic.name.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return jsonify({
            "data": [t.to_dict() for t in items],
            "meta": {"total": total, "limit": limit, "offset": offset},
        })

    @app.get("/topics/<id>")
    def get_topic(id: str):
        """
        Einzelnes Topic per ID (UUID) abrufen.
        """
        t = Topic.query.get(id)
        if not t:
            return jsonify({"error": "Topic not found"}), 404
        return jsonify(t.to_dict())

    @app.post("/topics")
    def create_topic():
        """
        Neues Topic anlegen.
        """
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        description = payload.get("description")
        parent_id = payload.get("parentTopicID")

        if not name:
            return jsonify({"error": "Field 'name' is required"}), 422

        if parent_id:
            parent = Topic.query.get(parent_id)
            if not parent:
                return jsonify({"error": "parentTopicID not found"}), 422

        t = Topic(name=name, description=description, parent_topic_id=parent_id)
        db.session.add(t)
        db.session.commit()
        return jsonify(t.to_dict()), 201

    @app.put("/topics/<id>")
    def update_topic(id: str):
        """
        Topic aktualisieren (einfacher Partial-Update-Stil).
        """
        t = Topic.query.get(id)
        if not t:
            return jsonify({"error": "Topic not found"}), 404

        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or t.name).strip()
        description = payload.get("description", t.description)
        parent_id = payload.get("parentTopicID", t.parent_topic_id)

        if parent_id:
            parent = Topic.query.get(parent_id)
            if not parent:
                return jsonify({"error": "parentTopicID not found"}), 422

        t.name = name
        t.description = description
        t.parent_topic_id = parent_id
        db.session.commit()
        return jsonify(t.to_dict())

    @app.delete("/topics/<id>")
    def delete_topic(id: str):
        """
        Topic löschen.
        """
        t = Topic.query.get(id)
        if not t:
            return jsonify({"error": "Topic not found"}), 404

        has_skills = db.session.query(exists().where(Skill.topic_id == id)).scalar()
        if has_skills:
            return jsonify({"error": "Topic has skills; move or delete skills first"}), 409

        db.session.delete(t)
        db.session.commit()
        return "", 204

    # -------------------------------------------------------------------------
    # Skills: CRUD + Suche/Filter/Pagination
    # -------------------------------------------------------------------------
    @app.get("/skills")
    def list_skills():
        """
        Liste aller Skills (mit optionaler Suche/Topic-Filter und Pagination).
        """
        q = request.args.get("q")
        topic_id = request.args.get("topicId")

        # Hinweis: KEINE Datentyp-Prüfung; int() wirft bei ungültigen Werten einen 500-Fehler.
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = max(int(request.args.get("offset", 0)), 0)

        query = Skill.query
        if q:
            query = query.filter(Skill.name.ilike(f"%{q}%"))
        if topic_id:
            query = query.filter(Skill.topic_id == topic_id)

        total = query.count()
        items = (
            query.order_by(Skill.name.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return jsonify({
            "data": [s.to_dict() for s in items],
            "meta": {"total": total, "limit": limit, "offset": offset},
        })

    @app.get("/skills/<id>")
    def get_skill(id: str):
        """
        Einzelnen Skill per ID (UUID) abrufen.
        """
        s = Skill.query.get(id)
        if not s:
            return jsonify({"error": "Skill not found"}), 404
        return jsonify(s.to_dict())

    @app.post("/skills")
    def create_skill():
        """
        Neuen Skill anlegen.
        """
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        topic_id = payload.get("topicID") or payload.get("topicId")
        difficulty = (payload.get("difficulty") or "beginner").strip()

        if not name:
            return jsonify({"error": "Field 'name' is required"}), 422
        if not topic_id:
            return jsonify({"error": "Field 'topicID' is required"}), 422

        if not Topic.query.get(topic_id):
            return jsonify({"error": "topicID not found"}), 422

        s = Skill(name=name, topic_id=topic_id, difficulty=difficulty)
        db.session.add(s)
        db.session.commit()
        return jsonify(s.to_dict()), 201

    @app.put("/skills/<id>")
    def update_skill(id: str):
        """
        Skill aktualisieren (einfacher Partial-Update-Stil).
        """
        s = Skill.query.get(id)
        if not s:
            return jsonify({"error": "Skill not found"}), 404

        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or s.name).strip()
        topic_id = payload.get("topicID", payload.get("topicId", s.topic_id))
        difficulty = (payload.get("difficulty") or s.difficulty).strip()

        if not Topic.query.get(topic_id):
            return jsonify({"error": "topicID not found"}), 422

        s.name = name
        s.topic_id = topic_id
        s.difficulty = difficulty
        db.session.commit()
        return jsonify(s.to_dict())

    @app.delete("/skills/<id>")
    def delete_skill(id: str):
        """
        Skill löschen.
        """
        s = Skill.query.get(id)
        if not s:
            return jsonify({"error": "Skill not found"}), 404
        db.session.delete(s)
        db.session.commit()
        return "", 204

    # Ende create_app: die konfigurierte App an den Aufrufer zurückgeben
    return app


# Lokaler Dev-Start (nur wenn direkt ausgeführt)
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
