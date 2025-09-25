# app.py in topic_skill_service_example
import os
from flask import Flask, jsonify, request # Flask-Anwendung, JSON-Antworten und Request-Objekt
from flask_migrate import Migrate
from dotenv import load_dotenv
from models import db, Topic, Skill
from sqlalchemy import exists
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://app:app123@localhost:5432/topics_db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
Migrate(app, db)


CORS(app) 


@app.route('/')
def hello_world():
    """
    Basis-Endpunkt zur Überprüfung der Service-Erreichbarkeit.
    Gibt eine einfache "Hello World"-Nachricht zurück.
    """
    return 'Hello from Topic & Skill Service!'

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# --- TOPIC ENDPUNKTE ---

@app.route('/topics', methods=['GET'])
def get_topics():
    """
    Ruft alle verfügbaren Lern-Topics ab.
    """
    q = request.args.get("q")
    parent_id = request.args.get("parentId")
    try:
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
    except:
        return jsonify({"error": "limit/offset must be numbers"}), 422

    query = Topic.query
    if q:
        query = query.filter(Topic.name.ilike(f"%{q}%"))
    if parent_id:
        query = query.filter(Topic.parent_topic_id == parent_id)

    total = query.count()
    items = query.order_by(Topic.name.asc()).limit(limit).offset(offset).all()
    return {
        "data": [t.to_dict() for t in items],
        "meta": {"total": total, "limit": limit, "offset": offset}
        }


@app.route('/topics/<id>', methods=['GET'])
def get_topic_by_id(id):
    """
    Ruft ein einzelnes Lern-Topic anhand seiner ID ab.
    Gibt 404 Not Found zurück, wenn das Topic nicht gefunden wird.
    """
    topic = Topic.query.get(id)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    return topic.to_dict()


@app.route('/topics', methods=['POST'])
def create_topic():
    """
    Erstellt ein neues Lern-Topic.
    Erfordert 'name' und 'description' im JSON-Request-Body.
    Generiert eine eindeutige ID und speichert das Topic.
    """
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    description = payload.get("description")
    parent_id = payload.get("parentTopicID")

    if not name:
        return jsonify({"error": "Field 'name' is required."}), 422

    if parent_id:
        parent = Topic.query.get(parent_id)
        if not parent:
            return jsonify({"error": "parentTopicID not found"}), 422

    topic = Topic(name=name, description=description, parent_topic_id=parent_id)
    db.session.add(topic)
    db.session.commit()
    return topic.to_dict(), 201


@app.route('/topics/<id>', methods=['PUT'])
def update_topic(id):
    """
    Aktualisiert ein bestehendes Lern-Topic anhand seiner ID.
    Erfordert 'name' und 'description' im JSON-Request-Body für die vollständige Aktualisierung.
    """
    topic = Topic.query.get(id)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or topic.name).strip()
    description = payload.get("description", topic.description)
    parent_id = payload.get("parentTopicID", topic.parent_topic_id)

    if parent_id:
        parent = Topic.query.get(parent_id)
        if not parent:
            return jsonify({"error": "parentTopicID not found"}), 422
    
    topic.name = name
    topic.description = description
    topic.parent_topic_id = parent_id
    db.session.commit()
    return topic.to_dict()


@app.route('/topics/<id>', methods=['DELETE'])
def delete_topic(id):
    """
    Löscht ein Lern-Topic anhand seiner ID.
    Gibt 204 No Content zurück, wenn erfolgreich gelöscht.
    """
    topic = Topic.query.get(id)

    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    has_skills = db.session.query(exists().where(Skill.topic_id == id)).scalar()
    has_topics = db.session.query(exists().where(Topic.parent_topic_id == id)).scalar()

    if has_skills:
        return jsonify({"error": "The topic has dependent skills, cannot delete the topic"}), 409

    if has_topics:
        return jsonify({"error": "The topic has dependent topics, cannot delete the topic"}), 409

    db.session.delete(topic)
    db.session.commit()
    return "", 204


# --- SKILL ENDPUNKTE ---

@app.route('/skills', methods=['GET'])
def get_skills():
    """
    Ruft alle verfügbaren Lern-Skills ab.
    """
    q = request.args.get("q")
    topic_id = request.args.get("topicId")
    try:
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
    except:
        return jsonify({"error": "limit/offset must be numbers"}), 422

    query = Skill.query
    if q:
        query = query.filter(Skill.name.ilike(f"%{q}%"))
    if topic_id:
        query = query.filter(Skill.topic_id == topic_id)

    total = query.count()
    items = query.order_by(Skill.name.asc()).limit(limit).offset(offset).all()
    return {
        "data": [s.to_dict() for s in items],
        "meta": {"total": total, "limit": limit, "offset": offset}
    }
    

@app.route('/skills/<id>', methods=['GET'])
def get_skill_by_id(id):
    """
    Ruft einen einzelnen Lern-Skill anhand seiner ID ab.
    Gibt 404 Not Found zurück, wenn der Skill nicht gefunden wird.
    """
    skill = Skill.query.get(id)
    if not skill:
        return jsonify({"error": "Skill not found"}), 404
    return skill.to_dict()

@app.route('/skills', methods=['POST'])
def create_skill():
    """
    Erstellt einen neuen Lern-Skill.
    Erfordert 'name' und 'topicId' im JSON-Request-Body.
    Generiert eine eindeutige ID und speichert den Skill.
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

    skill = Skill(name=name, topic_id=topic_id, difficulty=difficulty)
    db.session.add(skill)
    db.session.commit()
    return skill.to_dict(), 201


@app.route('/skills/<id>', methods=['PUT'])
def update_skill(id):
    """
    Aktualisiert einen bestehenden Lern-Skill anhand seiner ID.
    Erfordert 'name' und 'topicId' im JSON-Request-Body für die vollständige Aktualisierung.
    """
    skill = Skill.query.get(id)
    if not skill:
        return jsonify({"error": "Skill not found"}), 404

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or skill.name).strip()
    topic_id = payload.get("topicID", payload.get("topicId", skill.topic_id))
    difficulty = (payload.get("difficulty") or skill.difficulty).strip()

    if not Topic.query.get(topic_id):
        return jsonify({"error": "topicID not found"}), 422

    skill.name = name
    skill.topic_id = topic_id
    skill.difficulty = difficulty
    db.session.commit()
    return skill.to_dict()


@app.route('/skills/<id>', methods=['DELETE'])
def delete_skill(id):
    """
    Löscht einen Lern-Skill anhand seiner ID.
    Gibt 204 No Content zurück, wenn erfolgreich gelöscht.
    """
    skill = Skill.query.get(id)
    if not skill:
        return jsonify({"error": "Skill not found"}), 404
    db.session.delete(skill)
    db.session.commit()
    return "", 204

if __name__ == '__main__':
    # Startet den Flask-Entwicklungsserver.
    # debug=True ermöglicht automatische Neuladung bei Codeänderungen und detailliertere Fehlermeldungen.
    # port=5000 legt den Port fest, auf dem der Server läuft (http://127.0.0.1:5000/).
    app.run(debug=True, port=5000)
