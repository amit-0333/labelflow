from datetime import datetime
from core.db import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="annotator")  # admin / annotator / reviewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    guidelines = db.Column(db.Text)
    label_options = db.Column(db.JSON, nullable=False)  # e.g. ["spam", "not_spam"]
    task_type = db.Column(db.String(30), default="classification")  # later: "pairwise"
    annotators_per_item = db.Column(db.Integer, default=2)  # 2-3
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    """One row of the uploaded CSV."""
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    extra_data = db.Column(db.JSON)  # other CSV columns
    # pending -> in_progress -> needs_review / completed
    status = db.Column(db.String(20), default="pending", index=True)
    is_gold = db.Column(db.Boolean, default=False)  # hidden test question
    gold_label = db.Column(db.String(100))
    final_label = db.Column(db.String(100))
    final_source = db.Column(db.String(20))  # "consensus" or "reviewer"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Assignment(db.Model):
    """Who has claimed which task. The unique rule prevents double-claiming by the same person."""
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="assigned")  # assigned / submitted
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("task_id", "user_id"),)


class Annotation(db.Model):
    """HUMAN labels only."""
    __tablename__ = "annotations"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    time_taken_ms = db.Column(db.Integer)       # for speed checks (Phase 12)
    accepted_ai = db.Column(db.Boolean)         # True/False if AI suggestion was shown, else NULL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("task_id", "user_id"),)


class AIPrediction(db.Model):
    """AI labels only, kept separate from human labels."""
    __tablename__ = "ai_predictions"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    model_name = db.Column(db.String(100))
    label = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReviewDecision(db.Model):
    """Reviewer's final decision on a disagreement."""
    __tablename__ = "review_decisions"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, unique=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)