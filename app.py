# app.py
# The single entry point for the whole site.
# Run with:  python app.py
# Then open: http://127.0.0.1:5000

import os
import re
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify, abort, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from templates.story_model import TOPICS, get_story
from quiz import get_quiz_node, QUIZ_DATA  # quiz_data/*.json is already loaded when quiz.py is imported

# ---------- app + database setup ----------

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///itihas_explorer.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Needed for session (login). Set a real SECRET_KEY environment variable when you deploy.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-before-deploy")
db = SQLAlchemy(app)

story_cache = {}  # resets every time the program restarts


# ---------- database models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)  # the unique ID the user types
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    topic_id = db.Column(db.String(50), nullable=False)  # slug, e.g. "indus-valley"
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # a user can complete a topic only once
    __table_args__ = (db.UniqueConstraint("user_id", "topic_id", name="uq_user_topic"),)


with app.app_context():
    db.create_all()


# ---------- topic data (defined ONCE) ----------
# slug -> display name (same names as TOPICS in story_model)
SLUG_TO_TOPIC = {
    "mughal-empire": "Mughal Empire",
    "delhi-sultanate": "Delhi Sultanate",
    "vijayanagara-empire": "Vijayanagara Empire",
    "chola-empire": "Chola Empire",
    "maratha-empire": "Maratha Empire",
    "rajput-kingdoms": "Rajput Kingdoms",
    "sikh-empire": "Sikh Empire",
    "east-india-company": "British East India Company & Expansion",
    "revolt-1857": "Revolt of 1857",
    "early-nationalism": "Indian National Congress & Early Nationalism",
    "swadeshi-movement": "Swadeshi Movement",
    "gandhian-era": "Gandhian Era & Non-Cooperation Movement",
    "civil-disobedience": "Civil Disobedience & Quit India Movement",
    "independence-partition": "Indian Independence & Partition",
    "indus-valley": "Indus Valley Civilization",
    "vedic-period": "Vedic Period",
    "mahajanapadas": "Mahajanapadas & Rise of Magadha",
    "maurya-empire": "Maurya Empire",
    "gupta-empire": "Gupta Empire",
    "buddhism-jainism": "Buddhism & Jainism",
    "sangam-age": "Sangam Age & Ancient South India",
}

# slug -> the key quiz.py uses for that topic (the quiz_data/<file>.json name)
SLUG_TO_QUIZ_KEY = {
    "mughal-empire": "mughal-empire",
    "delhi-sultanate": "Delhi-sultanate",
    "vijayanagara-empire": "Vijayanagara-empire",
    "chola-empire": "chola-empire",
    "maratha-empire": "maratha_empire",
    "rajput-kingdoms": "rajput kingdoms",
    "sikh-empire": "sikh_empire",
    "east-india-company": "British East India Company & Expansion",
    "revolt-1857": "revolt_1857",
    "early-nationalism": "indian_national_congress",
    "swadeshi-movement": "swadeshi_movement",
    "gandhian-era": "Gandhian Era & Non-Cooperation Movement",
    "civil-disobedience": "Civil Disobedience & Quit India Movement",
    "independence-partition": "Indian Independence & Partition",
    "indus-valley": "Indus Valley Civilization",
    "vedic-period": "Vedic Period",
    "mahajanapadas": "Mahajanapadas & Rise of Magadha",
    "maurya-empire": "Maurya Empire",
    "gupta-empire": "Gupta Empire",
    "buddhism-jainism": "Buddhism & Jainism",
    "sangam-age": "Sangam Age & Ancient South India",
}

TOTAL_TOPICS = len(SLUG_TO_TOPIC)  # 21


# ---------- helpers ----------
def resolve_quiz_topic_key(topic_param):
    """
    Accepts a URL slug (e.g. 'buddhism-jainism') or an exact quiz_data key,
    and returns the real key QUIZ_DATA uses, or None if nothing matches.
    Tries, in order:
      1. topic_param as-is (already an exact quiz_data key)
      2. SLUG_TO_QUIZ_KEY mapping
      3. display name converted to the underscore filename pattern
         (every non-alphanumeric character becomes an underscore)
    """
    if not topic_param:
        return None

    if topic_param in QUIZ_DATA:
        return topic_param

    mapped = SLUG_TO_QUIZ_KEY.get(topic_param)
    if mapped in QUIZ_DATA:
        return mapped

    display_name = SLUG_TO_TOPIC.get(topic_param)
    if display_name:
        candidate = re.sub(r"[^A-Za-z0-9]", "_", display_name)
        if candidate in QUIZ_DATA:
            return candidate

    return None


def normalize_topic(topic):
    """Turn a slug into the display name used as the key in TOPICS.
    If it is already a display name, return it unchanged."""
    return SLUG_TO_TOPIC.get(topic, topic)


def current_user():
    """Return the logged-in User object, or None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)


# ---------- page routes ----------
@app.route("/")
def home():
    # index.html - topic menu / map
    return render_template("index.html", topics=list(TOPICS.keys()))


@app.route("/universe.html")
def universe():
    return render_template("universe.html")


@app.route("/simulation.html")
def simulation():
    quiz_slug = request.args.get("quiz")
    quiz_key = resolve_quiz_topic_key(quiz_slug)
    if quiz_slug and not quiz_key:
        return render_template("simulation.html", error=f'No quiz found for "{quiz_slug}"')
    return render_template("simulation.html", quiz_key=quiz_key)


@app.route("/mysteries.html")
def mysteries():
    return render_template("mysteries.html")


@app.route("/map_explorer.html")
def map_explorer():
    return render_template("map_explorer.html")


@app.route("/intro.html")
def intro():
    return render_template("intro.html")


@app.route("/india.html")
def india():
    return render_template("india.html")


@app.route("/roadmap.html")
def roadmap():
    return render_template("roadmap.html")


@app.route("/timeline.html")
def timeline():
    topic_slug = request.args.get("topic")
    era = request.args.get("era")
    topic_display_name = SLUG_TO_TOPIC.get(topic_slug)
    return render_template(
        "timeline.html",
        topic=topic_slug,
        era=era,
        topic_display_name=topic_display_name,
    )


@app.route("/story/<topic>")
def story_page(topic):
    if normalize_topic(topic) not in TOPICS:
        abort(404)
    # timeline.html - your existing template for showing a single topic;
    # it can call /generate-story and /get-quiz-question via fetch()
    return render_template("timeline.html", topic=topic)


# ---------- JSON API routes (called by your front-end JS) ----------
@app.route("/api/topics")
def api_topics():
    return jsonify(list(TOPICS.keys()))


@app.route("/generate-story", methods=["POST"])
def generate_story_route():
    data = request.get_json(silent=True) or {}
    topic = normalize_topic(data.get("topic"))
    if not topic or topic not in TOPICS:
        return jsonify({"error": "Invalid or missing topic"}), 400

    if topic in story_cache:
        return jsonify({"story": story_cache[topic]})  # cached this run

    story = get_story(topic)  # only generate if not cached this run
    story_cache[topic] = story
    return jsonify({"story": story})


@app.route("/get-quiz-question", methods=["POST"])
def get_quiz_question():
    data = request.get_json(silent=True) or {}
    topic_param = data.get("topic")
    path = data.get("path", "round1")

    quiz_key = resolve_quiz_topic_key(topic_param)
    if not quiz_key:
        return jsonify({
            "error": f'No quiz data found for topic "{topic_param}"',
            "available_topics": list(QUIZ_DATA.keys()),
        }), 404

    node = get_quiz_node(quiz_key, path)
    if not node:
        return jsonify({"error": f'Question not found for path "{path}"'}), 404
    return jsonify(node)


# ---------- user + progress API ----------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()

    if not username:
        return jsonify({"error": "Please enter your ID"}), 400
    if len(username) > 50 or not re.fullmatch(r"[a-z0-9_.-]+", username):
        return jsonify({"error": "ID can only have letters, numbers, _ . - (max 50 characters)"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:  # new user -> create automatically
        user = User(username=username, name=(data.get("name") or username)[:100])
        db.session.add(user)
        db.session.commit()

    session["user_id"] = user.id
    return jsonify({"ok": True, "username": user.username, "name": user.name})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"username": user.username, "name": user.name})


@app.route("/api/progress", methods=["GET"])
def get_progress():
    user = current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    done = [p.topic_id for p in Progress.query.filter_by(user_id=user.id).all()]
    return jsonify({"completed": done, "count": len(done), "total": TOTAL_TOPICS})


@app.route("/api/progress/<topic_id>", methods=["POST", "DELETE"])
def update_progress(topic_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    if topic_id not in SLUG_TO_TOPIC:
        return jsonify({"error": f'Unknown topic "{topic_id}"'}), 404

    already = Progress.query.filter_by(user_id=user.id, topic_id=topic_id).first()

    if request.method == "DELETE":  # un-mark the chapter
        if already:
            db.session.delete(already)
            db.session.commit()
        count = Progress.query.filter_by(user_id=user.id).count()
        return jsonify({"ok": True, "count": count, "total": TOTAL_TOPICS})

    if not already:
        try:
            db.session.add(Progress(user_id=user.id, topic_id=topic_id))
            db.session.commit()
        except IntegrityError:  # two requests at once -> it is already saved, that's fine
            db.session.rollback()

    count = Progress.query.filter_by(user_id=user.id).count()
    return jsonify({"ok": True, "count": count, "total": TOTAL_TOPICS})


if __name__ == "__main__":
    app.run(debug=True)