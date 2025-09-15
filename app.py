import os
import json # Bleibt importiert, da jsonify intern JSON verwendet und wir es für manuelle JSON-Konvertierungen nutzen könnten
import uuid # Für die Generierung eindeutiger IDs
from flask import Flask, jsonify, request # Flask-Anwendung, JSON-Antworten und Request-Objekt
from flask_migrate import Migrate # Für zukünftige Datenbankmigrationen (derzeit nicht genutzt)
from dotenv import load_dotenv
from models import db # Importiere die SQLAlchemy db-Instanz aus der models.py Datei

# Importiere unsere JsonDataManager-Klasse aus der data_manager.py Datei
from data_manager import JsonDataManager

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://app:app123@localhost:5432/topics_db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app) # Initialisiere die Datenbank mit der Flask-App
Migrate(app, db) # Initialisiere Migrate (derzeit ohne Datenbankmodelle)


# Definieren der Dateipfade für unsere Daten.
# os.path.dirname(__file__) gibt den Pfad des aktuellen Skripts zurück.
# os.path.join verbindet Pfadsegmente plattformunabhängig.
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TOPICS_FILE = os.path.join(DATA_DIR, 'topics.json')
SKILLS_FILE = os.path.join(DATA_DIR, 'skills.json')

# Erstelle eine Instanz unseres Datenmanagers.
# Diese Instanz wird verwendet, um Daten aus den JSON-Dateien zu lesen und zu schreiben.
data_manager = JsonDataManager()

@app.route('/')
def hello_world():
    """
    Basis-Endpunkt zur Überprüfung der Service-Erreichbarkeit.
    Gibt eine einfache "Hello World"-Nachricht zurück.
    """
    return 'Hello from Topic & Skill Service!'

# --- TOPIC ENDPUNKTE ---

@app.route('/topics', methods=['GET'])
def get_topics():
    """
    Ruft alle verfügbaren Lern-Topics ab.
    """
    topics = data_manager.read_data(TOPICS_FILE)
    return jsonify(topics)

@app.route('/topics/<id>', methods=['GET'])
def get_topic_by_id(id):
    """
    Ruft ein einzelnes Lern-Topic anhand seiner ID ab.
    Gibt 404 Not Found zurück, wenn das Topic nicht gefunden wird.
    """
    topics = data_manager.read_data(TOPICS_FILE)
    # Verwende 'next()' mit einem Generator-Ausdruck, um das erste passende Topic zu finden.
    # Wenn kein Topic gefunden wird, ist der Standardwert 'None'.
    topic = next((t for t in topics if t['id'] == id), None)
    if topic:
        return jsonify(topic)
    return jsonify({"error": "Topic not found"}), 404

@app.route('/topics', methods=['POST'])
def create_topic():
    """
    Erstellt ein neues Lern-Topic.
    Erfordert 'name' und 'description' im JSON-Request-Body.
    Generiert eine eindeutige ID und speichert das Topic.
    """
    new_topic_data = request.json
    # Grundlegende Validierung der eingehenden Daten
    if not new_topic_data or 'name' not in new_topic_data or 'description' not in new_topic_data:
        return jsonify({"error": "Name und Beschreibung für das Topic sind erforderlich"}), 400

    # Generiere eine universell eindeutige ID (UUID) für das neue Topic
    new_topic_id = str(uuid.uuid4())

    topic = {
        "id": new_topic_id,
        "name": new_topic_data['name'],
        "description": new_topic_data['description']
    }

    topics = data_manager.read_data(TOPICS_FILE)
    topics.append(topic)
    data_manager.write_data(TOPICS_FILE, topics)

    return jsonify(topic), 201 # 201 Created Statuscode für erfolgreiche Ressourcenerstellung

@app.route('/topics/<id>', methods=['PUT'])
def update_topic(id):
    """
    Aktualisiert ein bestehendes Lern-Topic anhand seiner ID.
    Erfordert 'name' und 'description' im JSON-Request-Body für die vollständige Aktualisierung.
    """
    updated_data = request.json
    if not updated_data or 'name' not in updated_data or 'description' not in updated_data:
        return jsonify({"error": "Name und Beschreibung für das Topic sind erforderlich"}), 400

    topics = data_manager.read_data(TOPICS_FILE)

    found_index = -1
    for i, t in enumerate(topics):
        if t['id'] == id:
            found_index = i
            break

    if found_index == -1:
        return jsonify({"error": "Topic not found"}), 404

    # Aktualisiere die Felder des gefundenen Topics
    topics[found_index]['name'] = updated_data['name']
    topics[found_index]['description'] = updated_data['description']

    data_manager.write_data(TOPICS_FILE, topics)

    return jsonify(topics[found_index]), 200 # 200 OK Statuscode für erfolgreiche Aktualisierung

@app.route('/topics/<id>', methods=['DELETE'])
def delete_topic(id):
    """
    Löscht ein Lern-Topic anhand seiner ID.
    Gibt 204 No Content zurück, wenn erfolgreich gelöscht.
    """
    topics = data_manager.read_data(TOPICS_FILE)

    found_index = -1
    for i, t in enumerate(topics):
        if t['id'] == id:
            found_index = i
            break

    if found_index == -1:
        return jsonify({"error": "Topic not found"}), 404

    # Entferne das Topic aus der Liste
    topics.pop(found_index)
    data_manager.write_data(TOPICS_FILE, topics)

    return '', 204 # 204 No Content Statuscode für erfolgreiche Löschung ohne Rückgabeinhalt

# --- SKILL ENDPUNKTE ---

@app.route('/skills', methods=['GET'])
def get_skills():
    """
    Ruft alle verfügbaren Lern-Skills ab.
    """
    skills = data_manager.read_data(SKILLS_FILE)
    return jsonify(skills)

@app.route('/skills/<id>', methods=['GET'])
def get_skill_by_id(id):
    """
    Ruft einen einzelnen Lern-Skill anhand seiner ID ab.
    Gibt 404 Not Found zurück, wenn der Skill nicht gefunden wird.
    """
    skills = data_manager.read_data(SKILLS_FILE)
    skill = next((s for s in skills if s['id'] == id), None)
    if skill:
        return jsonify(skill)
    return jsonify({"error": "Skill not found"}), 404

@app.route('/skills', methods=['POST'])
def create_skill():
    """
    Erstellt einen neuen Lern-Skill.
    Erfordert 'name' und 'topicId' im JSON-Request-Body.
    Generiert eine eindeutige ID und speichert den Skill.
    """
    new_skill_data = request.json
    if not new_skill_data or 'name' not in new_skill_data or 'topicId' not in new_skill_data:
        return jsonify({"error": "Name und Topic ID für den Skill sind erforderlich"}), 400

    new_skill_id = str(uuid.uuid4())
    skill = {
        "id": new_skill_id,
        "name": new_skill_data['name'],
        "topicId": new_skill_data['topicId'],
        "difficulty": new_skill_data.get('difficulty', 'unknown') # 'difficulty' ist optional
    }

    skills = data_manager.read_data(SKILLS_FILE)
    skills.append(skill)
    data_manager.write_data(SKILLS_FILE, skills)

    return jsonify(skill), 201

@app.route('/skills/<id>', methods=['PUT'])
def update_skill(id):
    """
    Aktualisiert einen bestehenden Lern-Skill anhand seiner ID.
    Erfordert 'name' und 'topicId' im JSON-Request-Body für die vollständige Aktualisierung.
    """
    updated_data = request.json
    if not updated_data or 'name' not in updated_data or 'topicId' not in updated_data:
        return jsonify({"error": "Name und Topic ID für den Skill sind erforderlich"}), 400

    skills = data_manager.read_data(SKILLS_FILE)

    found_index = -1
    for i, s in enumerate(skills):
        if s['id'] == id:
            found_index = i
            break

    if found_index == -1:
        return jsonify({"error": "Skill not found"}), 404

    # Aktualisiere die Felder des gefundenen Skills
    skills[found_index]['name'] = updated_data['name']
    skills[found_index]['topicId'] = updated_data['topicId']
    # 'difficulty' wird aktualisiert, wenn im Request vorhanden, sonst bleibt der alte Wert
    skills[found_index]['difficulty'] = updated_data.get('difficulty', skills[found_index].get('difficulty', 'unknown'))

    data_manager.write_data(SKILLS_FILE, skills)

    return jsonify(skills[found_index]), 200

@app.route('/skills/<id>', methods=['DELETE'])
def delete_skill(id):
    """
    Löscht einen Lern-Skill anhand seiner ID.
    Gibt 204 No Content zurück, wenn erfolgreich gelöscht.
    """
    skills = data_manager.read_data(SKILLS_FILE)

    found_index = -1
    for i, s in enumerate(skills):
        if s['id'] == id:
            found_index = i
            break

    if found_index == -1:
        return jsonify({"error": "Skill not found"}), 404

    skills.pop(found_index)
    data_manager.write_data(SKILLS_FILE, skills)

    return '', 204

if __name__ == '__main__':
    # Startet den Flask-Entwicklungsserver.
    # debug=True ermöglicht automatische Neuladung bei Codeänderungen und detailliertere Fehlermeldungen.
    # port=5000 legt den Port fest, auf dem der Server läuft (http://127.0.0.1:5000/).
    app.run(debug=True, port=5000)
