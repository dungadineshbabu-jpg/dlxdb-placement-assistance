from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)  # Added email verification field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    resume_analysis = db.relationship('ResumeAnalysis', backref='user', uselist=False)
    answers = db.relationship('AnswerEvaluation', backref='user', lazy=True)
    weak_areas = db.relationship('WeakArea', backref='user', lazy=True)
    roadmap = db.relationship('Roadmap', backref='user', uselist=False)
    resume_data = db.relationship('ResumeData', backref='user', uselist=False)
    company_resumes = db.relationship('CompanyResume', backref='user', lazy=True)
    resume_versions = db.relationship('ResumeVersion', backref='user', lazy=True)
    job_applications = db.relationship('JobApplication', backref='user', lazy=True)
    certificates = db.relationship('Certificate', backref='user', lazy=True)
    gd_sessions = db.relationship('GroupDiscussion', backref='user', lazy=True)
    contest_entries = db.relationship('CodingContest', backref='user', lazy=True)
    achievements = db.relationship('Achievement', backref='user', lazy=True)
    company_placements = db.relationship('CompanyPlacement', backref='user', lazy=True)

class ResumeAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resume_text = db.Column(db.Text, nullable=False)
    target_company = db.Column(db.String(100), nullable=False)
    job_role = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.Text)
    projects = db.Column(db.Text)
    education = db.Column(db.String(200))
    strengths = db.Column(db.Text)
    weak_areas_resume = db.Column(db.Text)
    missing_skills = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InterviewQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnswerEvaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('interview_question.id'))
    user_answer = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    improved_answer = db.Column(db.Text)
    clarity_score = db.Column(db.Float)
    confidence_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WeakArea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(50))
    severity = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Roadmap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_questions_answered = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float, default=0)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

class ResumeData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    summary = db.Column(db.Text)
    skills = db.Column(db.Text)
    projects = db.Column(db.Text)
    education = db.Column(db.Text)
    experience = db.Column(db.Text)
    template_choice = db.Column(db.String(50), default='professional')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ========== NEW MODULES (9–20, 23) ==========

class CompanyPlacement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    aptitude_score = db.Column(db.Float, default=0)
    coding_score = db.Column(db.Float, default=0)
    interview_score = db.Column(db.Float, default=0)
    overall_score = db.Column(db.Float, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    job_role = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='Applied')
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    interview_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    certificate_name = db.Column(db.String(200), nullable=False)
    issuing_authority = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    certificate_file = db.Column(db.String(500), nullable=True)
    verified = db.Column(db.Boolean, default=False)

class GroupDiscussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    user_response = db.Column(db.Text, nullable=False)
    communication_score = db.Column(db.Float, default=0)
    grammar_score = db.Column(db.Float, default=0)
    confidence_score = db.Column(db.Float, default=0)
    overall_score = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CodingContest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contest_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, default=0)
    rank = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_name = db.Column(db.String(100), nullable=False)
    badge_type = db.Column(db.String(50))
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)

class CompanyResume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    optimized_resume = db.Column(db.Text, nullable=True)
    ats_score = db.Column(db.Float, default=0)
    readiness_score = db.Column(db.Float, default=0)
    missing_skills = db.Column(db.Text, nullable=True)
    optimized_sections = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ResumeVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    version_name = db.Column(db.String(100), nullable=False)
    resume_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)