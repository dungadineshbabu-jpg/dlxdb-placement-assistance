from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import PyPDF2
from datetime import datetime
import random
import logging

from database import db, User, ResumeAnalysis, InterviewQuestion, AnswerEvaluation, WeakArea, Roadmap, UserProgress, ResumeData
from database import CompanyPlacement, JobApplication, Certificate, GroupDiscussion, CodingContest, Achievement, CompanyResume, ResumeVersion
from resume_parser import ResumeParser
from ai_engine import AIEngine
from company_resume_optimizer import CompanyResumeOptimizer
from email_utils import generate_verification_token, confirm_verification_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_assistant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

resume_optimizer = CompanyResumeOptimizer()

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
    return text

def award_badge(user_id, badge_name, badge_type):
    existing = Achievement.query.filter_by(user_id=user_id, badge_name=badge_name).first()
    if not existing:
        badge = Achievement(user_id=user_id, badge_name=badge_name, badge_type=badge_type)
        db.session.add(badge)
        db.session.commit()

def evaluate_code_quality(code):
    score = 50
    if len(code.strip()) > 100:
        score += 10
    if 'def' in code or 'function' in code:
        score += 15
    if 'return' in code:
        score += 10
    if '#' in code or '//' in code:
        score += 5
    if 'try' in code or 'except' in code:
        score += 10
    return min(100, score)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- AUTHENTICATION ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        pwd = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if pwd != confirm:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        user = User(name=name, email=email, password=generate_password_hash(pwd))
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pwd = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, pwd):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

# ---------- EMAIL VERIFICATION ROUTES ----------
@app.route('/send_verification')
@login_required
def send_verification():
    """Send email verification link to user"""
    token = generate_verification_token(current_user.email)
    verification_url = url_for('verify_email', token=token, _external=True)
    
    # In production, send actual email
    flash(f'Verification link (demo): {verification_url}', 'info')
    return redirect(url_for('dashboard'))

@app.route('/verify_email/<token>')
def verify_email(token):
    """Verify user email address using token"""
    email = confirm_verification_token(token)
    if email:
        user = User.query.filter_by(email=email).first()
        if user:
            # Add email_verified column to User model if not exists
            if not hasattr(user, 'email_verified'):
                # You need to add this column to database
                pass
            else:
                user.email_verified = True
                db.session.commit()
            flash('Email verified successfully!', 'success')
        else:
            flash('User not found.', 'danger')
    else:
        flash('Invalid or expired token.', 'danger')
    return redirect(url_for('login'))

# ---------- DASHBOARD & RESUME PROCESSING ----------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/process_resume', methods=['POST'])
@login_required
def process_resume():
    company = request.form.get('company')
    role = request.form.get('role')
    if not company or not role:
        flash('Please provide both company and job role!', 'danger')
        return redirect(url_for('dashboard'))
    if 'resume' not in request.files:
        flash('Please upload a resume file!', 'danger')
        return redirect(url_for('dashboard'))
    file = request.files['resume']
    if file.filename == '':
        flash('Select a file!', 'danger')
        return redirect(url_for('dashboard'))
    if not allowed_file(file.filename):
        flash('Only PDF or TXT files allowed!', 'danger')
        return redirect(url_for('dashboard'))
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{current_user.id}_{filename}")
    file.save(filepath)
    if os.path.getsize(filepath) > app.config['MAX_CONTENT_LENGTH']:
        os.remove(filepath)
        flash('File too large! Maximum 5MB allowed.', 'danger')
        return redirect(url_for('dashboard'))
    if filename.endswith('.pdf'):
        resume_text = extract_text_from_pdf(filepath)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            resume_text = f.read()
    os.remove(filepath)
    if not resume_text.strip():
        flash('Could not extract text from resume.', 'danger')
        return redirect(url_for('dashboard'))
    skills = ResumeParser.extract_skills(resume_text)
    projects = ResumeParser.extract_projects(resume_text)
    education = ResumeParser.extract_education(resume_text)
    strengths = ResumeParser.analyze_strengths(skills, role)
    weak_resume = ResumeParser.identify_weak_areas(skills, role)
    missing = ResumeParser.get_missing_skills(skills, company)
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if analysis:
        analysis.resume_text = resume_text
        analysis.target_company = company
        analysis.job_role = role
        analysis.skills = json.dumps(skills)
        analysis.projects = json.dumps(projects)
        analysis.education = education
        analysis.strengths = json.dumps(strengths)
        analysis.weak_areas_resume = json.dumps(weak_resume)
        analysis.missing_skills = json.dumps(missing)
    else:
        analysis = ResumeAnalysis(user_id=current_user.id, resume_text=resume_text, target_company=company, job_role=role,
                                  skills=json.dumps(skills), projects=json.dumps(projects), education=education,
                                  strengths=json.dumps(strengths), weak_areas_resume=json.dumps(weak_resume), missing_skills=json.dumps(missing))
        db.session.add(analysis)
    WeakArea.query.filter_by(user_id=current_user.id).delete()
    for w in weak_resume:
        db.session.add(WeakArea(user_id=current_user.id, topic=w, source='resume', severity=7))
    InterviewQuestion.query.filter_by(user_id=current_user.id).delete()
    questions = AIEngine.generate_questions(company, role, missing, weak_resume)
    for q in questions:
        db.session.add(InterviewQuestion(user_id=current_user.id, question_text=q['text'], question_type=q['type']))
    db.session.commit()
    session['company'] = company
    session['role'] = role
    flash('Resume analyzed successfully!', 'success')
    return redirect(url_for('preparation'))

# ---------- PREPARATION (Text Q&A) ----------
@app.route('/preparation')
@login_required
def preparation():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        flash('Please upload resume first!', 'warning')
        return redirect(url_for('dashboard'))
    questions = InterviewQuestion.query.filter_by(user_id=current_user.id).all()
    answers = AnswerEvaluation.query.filter_by(user_id=current_user.id).all()
    weak = WeakArea.query.filter_by(user_id=current_user.id).all()
    strengths = json.loads(analysis.strengths) if analysis.strengths else []
    missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
    return render_template('preparation.html', analysis=analysis, questions=questions, answers=answers, weak_areas=weak, strengths=strengths, missing_skills=missing)

@app.route('/evaluate_answer', methods=['POST'])
@login_required
def evaluate_answer():
    data = request.get_json()
    qid = data.get('question_id')
    answer = data.get('answer')
    question = InterviewQuestion.query.get(qid)
    if not question or question.user_id != current_user.id:
        return jsonify({'error': 'Invalid question'}), 400
    eval_res = AIEngine.evaluate_answer(question.question_text, answer, question.question_type)
    existing = AnswerEvaluation.query.filter_by(user_id=current_user.id, question_id=qid).first()
    if existing:
        existing.user_answer = answer
        existing.score = eval_res['score']
        existing.feedback = eval_res['feedback']
        existing.improved_answer = eval_res['improved_answer']
        existing.clarity_score = eval_res['clarity_score']
        existing.confidence_score = eval_res['confidence_score']
    else:
        db.session.add(AnswerEvaluation(user_id=current_user.id, question_id=qid, user_answer=answer, score=eval_res['score'],
                                        feedback=eval_res['feedback'], improved_answer=eval_res['improved_answer'],
                                        clarity_score=eval_res['clarity_score'], confidence_score=eval_res['confidence_score']))
    if eval_res['score'] < 5:
        topic = f"Answering {question.question_type} question: {question.question_text[:50]}"
        if not WeakArea.query.filter_by(user_id=current_user.id, topic=topic).first():
            db.session.add(WeakArea(user_id=current_user.id, topic=topic, source='answer', severity=8))
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        db.session.add(progress)
    total = AnswerEvaluation.query.filter_by(user_id=current_user.id).count()
    avg = db.session.query(db.func.avg(AnswerEvaluation.score)).filter_by(user_id=current_user.id).scalar() or 0
    progress.total_questions_answered = total
    progress.average_score = avg
    progress.last_active = datetime.utcnow()
    db.session.commit()
    return jsonify(eval_res)

# ---------- TEXT MOCK INTERVIEW ----------
@app.route('/mock_interview')
@login_required
def mock_interview():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        flash('Please upload resume first', 'warning')
        return redirect(url_for('dashboard'))
    questions = InterviewQuestion.query.filter_by(user_id=current_user.id).all()
    if not questions:
        missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
        weak = [w.topic for w in WeakArea.query.filter_by(user_id=current_user.id).all()]
        qs = AIEngine.generate_questions(analysis.target_company, analysis.job_role, missing, weak)
        for q in qs:
            db.session.add(InterviewQuestion(user_id=current_user.id, question_text=q['text'], question_type=q['type']))
        db.session.commit()
        questions = InterviewQuestion.query.filter_by(user_id=current_user.id).all()
    q_list = [{'id': q.id, 'text': q.question_text, 'type': q.question_type} for q in questions]
    return render_template('mock_interview.html', questions=q_list)

@app.route('/evaluate_mock', methods=['POST'])
@login_required
def evaluate_mock():
    data = request.get_json()
    qid = data.get('question_id')
    answer = data.get('answer')
    question = InterviewQuestion.query.get(qid)
    if not question or question.user_id != current_user.id:
        return jsonify({'error': 'Invalid question'}), 400
    eval_res = AIEngine.evaluate_answer(question.question_text, answer, question.question_type)
    existing = AnswerEvaluation.query.filter_by(user_id=current_user.id, question_id=qid).first()
    if existing:
        existing.user_answer = answer
        existing.score = eval_res['score']
        existing.feedback = eval_res['feedback']
        existing.improved_answer = eval_res['improved_answer']
    else:
        db.session.add(AnswerEvaluation(user_id=current_user.id, question_id=qid, user_answer=answer, score=eval_res['score'],
                                        feedback=eval_res['feedback'], improved_answer=eval_res['improved_answer'],
                                        clarity_score=eval_res['clarity_score'], confidence_score=eval_res['confidence_score']))
    if eval_res['score'] < 5:
        topic = f"Mock Q: {question.question_text[:50]}"
        if not WeakArea.query.filter_by(user_id=current_user.id, topic=topic).first():
            db.session.add(WeakArea(user_id=current_user.id, topic=topic, source='mock', severity=8))
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        db.session.add(progress)
    total = AnswerEvaluation.query.filter_by(user_id=current_user.id).count()
    avg = db.session.query(db.func.avg(AnswerEvaluation.score)).filter_by(user_id=current_user.id).scalar() or 0
    progress.total_questions_answered = total
    progress.average_score = avg
    progress.last_active = datetime.utcnow()
    db.session.commit()
    return jsonify({'score': eval_res['score'], 'feedback': eval_res['feedback'], 'improved_answer': eval_res['improved_answer']})

# ---------- INTERVIEW CHATBOT ----------
@app.route('/interview_chatbot')
@login_required
def interview_chatbot():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        flash('Please upload your resume first!', 'warning')
        return redirect(url_for('dashboard'))
    if 'chatbot_questions' not in session:
        missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
        weak = [w.topic for w in WeakArea.query.filter_by(user_id=current_user.id).all()]
        questions_data = AIEngine.generate_questions(analysis.target_company, analysis.job_role, missing, weak)
        session['chatbot_questions'] = questions_data
        session['chatbot_index'] = 0
        session['chatbot_history'] = []
    return render_template('interview_chatbot.html', company=analysis.target_company, role=analysis.job_role, total_questions=len(session.get('chatbot_questions', [])))

@app.route('/chatbot_get_question', methods=['GET'])
@login_required
def chatbot_get_question():
    questions = session.get('chatbot_questions', [])
    index = session.get('chatbot_index', 0)
    if index >= len(questions):
        return jsonify({'finished': True})
    q = questions[index]
    return jsonify({'finished': False, 'question': q['text'], 'type': q['type'], 'index': index+1, 'total': len(questions)})

@app.route('/chatbot_submit_answer', methods=['POST'])
@login_required
def chatbot_submit_answer():
    data = request.get_json()
    user_answer = data.get('answer', '')
    index = session.get('chatbot_index', 0)
    questions = session.get('chatbot_questions', [])
    if index >= len(questions):
        return jsonify({'finished': True})
    current_q = questions[index]
    eval_res = AIEngine.evaluate_answer(current_q['text'], user_answer, current_q['type'])
    history = session.get('chatbot_history', [])
    history.append({'question': current_q['text'], 'type': current_q['type'], 'answer': user_answer, 'score': eval_res['score'], 'feedback': eval_res['feedback']})
    session['chatbot_history'] = history
    if eval_res['score'] < 5:
        topic = f"Chatbot Q: {current_q['text'][:50]}"
        if not WeakArea.query.filter_by(user_id=current_user.id, topic=topic).first():
            db.session.add(WeakArea(user_id=current_user.id, topic=topic, source='chatbot', severity=7))
            db.session.commit()
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        db.session.add(progress)
    total_answers = AnswerEvaluation.query.filter_by(user_id=current_user.id).count() + 1
    new_avg = (progress.average_score * progress.total_questions_answered + eval_res['score']) / total_answers if total_answers > 0 else eval_res['score']
    progress.total_questions_answered = total_answers
    progress.average_score = new_avg
    progress.last_active = datetime.utcnow()
    db.session.commit()
    session['chatbot_index'] = index + 1
    return jsonify({'score': eval_res['score'], 'feedback': eval_res['feedback'], 'improved_answer': eval_res['improved_answer'], 'next_index': index+1, 'finished': index+1 >= len(questions)})

@app.route('/chatbot_reset', methods=['POST'])
@login_required
def chatbot_reset():
    session.pop('chatbot_questions', None)
    session.pop('chatbot_index', None)
    session.pop('chatbot_history', None)
    return jsonify({'status': 'reset'})

# ---------- VOICE INTERVIEW ----------
@app.route('/voice_interview')
@login_required
def voice_interview():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        flash('Please upload your resume first!', 'warning')
        return redirect(url_for('dashboard'))
    skills = json.loads(analysis.skills) if analysis.skills else []
    missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
    weak = [w.topic for w in WeakArea.query.filter_by(user_id=current_user.id).all()]
    interview_rounds = AIEngine.generate_round_questions(analysis.target_company, analysis.job_role, skills, missing, weak)
    session['voice_rounds'] = interview_rounds
    session['voice_current_round'] = 'introduction'
    session['voice_q_index'] = 0
    session['voice_history'] = []
    return render_template('voice_interview.html', company=analysis.target_company, role=analysis.job_role)

@app.route('/voice_interview_next', methods=['GET'])
@login_required
def voice_interview_next():
    rounds = session.get('voice_rounds', {})
    current_round = session.get('voice_current_round')
    q_index = session.get('voice_q_index', 0)
    round_order = ['introduction', 'hr', 'technical', 'non_technical']
    if not current_round:
        current_round = round_order[0]
        session['voice_current_round'] = current_round
    round_data = rounds.get(current_round, {})
    questions = round_data.get('questions', [])
    if q_index >= len(questions):
        next_idx = round_order.index(current_round) + 1
        if next_idx < len(round_order):
            session['voice_current_round'] = round_order[next_idx]
            session['voice_q_index'] = 0
            current_round = round_order[next_idx]
            round_data = rounds.get(current_round, {})
            questions = round_data.get('questions', [])
            if questions:
                return jsonify({'type': 'round_transition', 'round_name': round_data.get('name', current_round.capitalize()), 'question': questions[0], 'question_index': 1, 'total_in_round': len(questions), 'rounds_completed': next_idx})
            else:
                return jsonify({'finished': True})
        else:
            return jsonify({'finished': True})
    return jsonify({'type': 'question', 'round_name': round_data.get('name', current_round.capitalize()), 'question': questions[q_index], 'question_index': q_index+1, 'total_in_round': len(questions), 'rounds_completed': round_order.index(current_round)})

@app.route('/voice_interview_submit', methods=['POST'])
@login_required
def voice_interview_submit():
    data = request.get_json()
    user_answer = data.get('answer', '')
    current_round = session.get('voice_current_round')
    q_index = session.get('voice_q_index', 0)
    rounds = session.get('voice_rounds', {})
    round_data = rounds.get(current_round, {})
    questions = round_data.get('questions', [])
    current_question = questions[q_index] if q_index < len(questions) else ""
    score, feedback = AIEngine.evaluate_conversational(user_answer)
    history = session.get('voice_history', [])
    history.append({'round': current_round, 'question': current_question, 'answer': user_answer, 'score': score})
    session['voice_history'] = history
    if score < 5:
        topic = f"Voice Interview - {current_round}: {current_question[:50]}"
        if not WeakArea.query.filter_by(user_id=current_user.id, topic=topic).first():
            db.session.add(WeakArea(user_id=current_user.id, topic=topic, source='voice_interview', severity=8))
            db.session.commit()
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        db.session.add(progress)
    total_answers = AnswerEvaluation.query.filter_by(user_id=current_user.id).count() + 1
    new_avg = (progress.average_score * progress.total_questions_answered + score) / total_answers if total_answers > 0 else score
    progress.total_questions_answered = total_answers
    progress.average_score = new_avg
    progress.last_active = datetime.utcnow()
    db.session.commit()
    session['voice_q_index'] = q_index + 1
    return jsonify({'score': score, 'feedback': feedback, 'next_index': q_index+1})

@app.route('/voice_interview_reset', methods=['POST'])
@login_required
def voice_interview_reset():
    session.pop('voice_rounds', None)
    session.pop('voice_current_round', None)
    session.pop('voice_q_index', None)
    session.pop('voice_history', None)
    return jsonify({'status': 'reset'})

# ---------- DETAILED ANALYSIS ----------
@app.route('/analysis')
@login_required
def analysis():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        flash('No resume found.', 'warning')
        return redirect(url_for('dashboard'))
    skills = json.loads(analysis.skills) if analysis.skills else []
    projects = json.loads(analysis.projects) if analysis.projects else []
    strengths = json.loads(analysis.strengths) if analysis.strengths else []
    weak_resume = json.loads(analysis.weak_areas_resume) if analysis.weak_areas_resume else []
    missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
    return render_template('analysis.html', skills=skills, projects=projects, strengths=strengths, weak_resume=weak_resume, missing=missing, education=analysis.education, company=analysis.target_company, role=analysis.job_role)

# ---------- MENTOR CHAT ----------
@app.route('/mentor')
@login_required
def mentor():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    company = analysis.target_company if analysis else "your target company"
    role = analysis.job_role if analysis else "the role"
    return render_template('mentor.html', company=company, role=role)

@app.route('/ask_mentor', methods=['POST'])
@login_required
def ask_mentor():
    data = request.get_json()
    user_question = data.get('question', '').lower()
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    company = analysis.target_company if analysis else "the company"
    role = analysis.job_role if analysis else "the role"
    if 'resume' in user_question:
        reply = f"Based on your resume, to improve for {company} {role}, tailor your resume with action verbs and quantify achievements."
    elif 'prepare' in user_question or 'preparation' in user_question:
        reply = f"For {company} {role}, focus on DSA, system design, and company values. Practice mock interviews daily."
    elif 'company' in user_question:
        reply = f"{company} looks for problem-solving skills and cultural fit. Research their leadership principles (Amazon), Googleyness (Google), or growth mindset (Microsoft)."
    elif 'technical' in user_question:
        reply = "Practice coding on LeetCode (easy-medium), review OS, DBMS, networks, and build projects."
    elif 'hr' in user_question or 'behavioral' in user_question:
        reply = "Use STAR method (Situation, Task, Action, Result) for behavioral questions."
    elif 'weakness' in user_question or 'weak area' in user_question:
        weak = WeakArea.query.filter_by(user_id=current_user.id).all()
        if weak:
            topics = [w.topic for w in weak[:3]]
            reply = f"Your weak areas: {', '.join(topics)}. Focus on improving these."
        else:
            reply = "No major weak areas detected yet. Keep practicing!"
    else:
        reply = f"I'm your AI mentor for {company} {role}. Ask me about resume, interview questions, company culture, or weak areas."
    return jsonify({'reply': reply})

# ---------- APTITUDE ----------
aptitude_questions = [
    {"q": "If a train travels 60 km in 1 hour, how far in 45 minutes?", "options": ["40 km","45 km","50 km","55 km"], "ans": "40 km"},
    {"q": "What is 15% of 200?", "options": ["20","25","30","35"], "ans": "30"},
    {"q": "Solve: 8 + 4 × 2 - 6 ÷ 3", "options": ["14","12","10","16"], "ans": "14"},
    {"q": "Average of 5 numbers is 20. Remove one, average becomes 18. Removed number?", "options": ["28","30","26","24"], "ans": "28"},
    {"q": "Buy cycle for ₹1200, sell at 10% loss. Selling price?", "options": ["₹1080","₹1100","₹1120","₹1000"], "ans": "₹1080"}
]

@app.route('/aptitude')
@login_required
def aptitude():
    q = random.choice(aptitude_questions)
    session['aptitude_answer'] = q['ans']
    return render_template('aptitude.html', question=q['q'], options=q['options'])

@app.route('/check_aptitude', methods=['POST'])
@login_required
def check_aptitude():
    user_ans = request.form.get('answer')
    correct = session.get('aptitude_answer')
    if user_ans == correct:
        flash('✅ Correct! Great job!', 'success')
        award_badge(current_user.id, 'Aptitude Expert', 'Aptitude')
    else:
        flash(f'❌ Wrong! Correct: {correct}', 'danger')
    return redirect(url_for('aptitude'))

# ---------- LEADERBOARD ----------
@app.route('/leaderboard')
@login_required
def leaderboard():
    users_data = []
    for u in User.query.all():
        prog = UserProgress.query.filter_by(user_id=u.id).first()
        avg = prog.average_score if prog else 0
        total = prog.total_questions_answered if prog else 0
        users_data.append({'name': u.name, 'email': u.email, 'avg_score': round(avg,1), 'total_answers': total})
    users_data.sort(key=lambda x: x['avg_score'], reverse=True)
    return render_template('leaderboard.html', users=users_data)

# ---------- RESUME BUILDER & TEMPLATES ----------
@app.route('/resume_templates')
@login_required
def resume_templates():
    return render_template('resume_templates.html')

@app.route('/resume_builder')
@login_required
def resume_builder():
    rd = ResumeData.query.filter_by(user_id=current_user.id).first()
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    parsed_skills = json.loads(analysis.skills) if analysis and analysis.skills else []
    parsed_projects = json.loads(analysis.projects) if analysis and analysis.projects else []
    parsed_education = analysis.education if analysis else ""
    if rd:
        full_name = rd.full_name or current_user.name
        email = rd.email or current_user.email
        phone = rd.phone or ""
        address = rd.address or ""
        summary = rd.summary or ""
        skills_list = json.loads(rd.skills) if rd.skills else parsed_skills
        projects_list = json.loads(rd.projects) if rd.projects else [{"title": p, "description": ""} for p in parsed_projects]
        education_list = json.loads(rd.education) if rd.education else [{"degree": parsed_education, "institution": "", "year": ""}]
        experience_list = json.loads(rd.experience) if rd.experience else [{"title": "", "company": "", "duration": "", "description": ""}]
        template_choice = rd.template_choice
    else:
        full_name = current_user.name
        email = current_user.email
        phone = ""
        address = ""
        summary = ""
        skills_list = parsed_skills
        projects_list = [{"title": p, "description": ""} for p in parsed_projects]
        education_list = [{"degree": parsed_education, "institution": "", "year": ""}]
        experience_list = [{"title": "", "company": "", "duration": "", "description": ""}]
        template_choice = "professional"
    return render_template('resume_builder.html', full_name=full_name, email=email, phone=phone, address=address,
                          summary=summary, skills_list=skills_list, projects_list=projects_list,
                          education_list=education_list, experience_list=experience_list, template_choice=template_choice)

@app.route('/save_resume_data', methods=['POST'])
@login_required
def save_resume_data():
    data = request.get_json()
    rd = ResumeData.query.filter_by(user_id=current_user.id).first()
    if not rd:
        rd = ResumeData(user_id=current_user.id)
        db.session.add(rd)
    rd.full_name = data.get('full_name')
    rd.email = data.get('email')
    rd.phone = data.get('phone')
    rd.address = data.get('address')
    rd.summary = data.get('summary')
    rd.skills = json.dumps(data.get('skills', []))
    rd.projects = json.dumps(data.get('projects', []))
    rd.education = json.dumps(data.get('education', []))
    rd.experience = json.dumps(data.get('experience', []))
    rd.template_choice = data.get('template_choice', 'professional')
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/preview_resume')
@login_required
def preview_resume():
    rd = ResumeData.query.filter_by(user_id=current_user.id).first()
    if not rd:
        flash('Please build your resume first.', 'warning')
        return redirect(url_for('resume_builder'))
    skills = json.loads(rd.skills) if rd.skills else []
    projects = json.loads(rd.projects) if rd.projects else []
    education = json.loads(rd.education) if rd.education else []
    experience = json.loads(rd.experience) if rd.experience else []
    return render_template('resume_preview.html', full_name=rd.full_name, email=rd.email, phone=rd.phone, address=rd.address,
                          summary=rd.summary, skills=skills, projects=projects, education=education, experience=experience,
                          template=rd.template_choice)

# ---------- CODE PRACTICE ----------
@app.route('/code_practice')
@login_required
def code_practice():
    return render_template('code_practice.html')

# ---------- ROADMAP & TIPS APIs ----------
@app.route('/get_roadmap')
@login_required
def get_roadmap():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        return jsonify({'error': 'No resume'}), 400
    weak_topics = [w.topic for w in WeakArea.query.filter_by(user_id=current_user.id).all()]
    missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    avg = progress.average_score if progress else 0
    roadmap, platforms = AIEngine.generate_roadmap(weak_topics, missing, analysis.target_company, analysis.job_role, avg)
    existing = Roadmap.query.filter_by(user_id=current_user.id).first()
    if existing:
        existing.plan_data = json.dumps(roadmap)
        existing.updated_at = datetime.utcnow()
    else:
        db.session.add(Roadmap(user_id=current_user.id, plan_data=json.dumps(roadmap)))
    db.session.commit()
    return jsonify({'roadmap': roadmap, 'platforms': platforms, 'weak_areas': weak_topics[:5], 'avg_score': avg})

@app.route('/resume_suggestions')
@login_required
def resume_suggestions():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        return jsonify({'error': 'No resume'}), 400
    skills = json.loads(analysis.skills) if analysis.skills else []
    missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
    sug = []
    if len(skills) < 5:
        sug.append("Add more relevant technical skills.")
    if missing:
        sug.append(f"Include projects demonstrating: {', '.join(missing[:3])}")
    sug.extend(["Use action verbs and quantify achievements.", "Tailor summary to job description.", "Add GitHub/LinkedIn links."])
    return jsonify({'suggestions': sug})

@app.route('/motivation_tip')
@login_required
def motivation_tip():
    tips = ["💪 Consistency beats intensity. Study 2 hours daily!", "🎯 Set small daily goals.", "📝 Review mistakes daily.",
            "🧠 Practice mock interviews.", "⏰ Use Pomodoro technique.", "🌟 Visualize success.", "🤝 Join study groups."]
    return jsonify({'tip': random.choice(tips)})

# ========== MODULES 9–20, 23 ==========

# MODULE 9: Company Placement Dashboard
@app.route('/company_dashboard')
@login_required
def company_dashboard():
    companies = ['TCS', 'Infosys', 'Google', 'Amazon', 'Microsoft', 'Wipro', 'Accenture']
    company_data = []
    for company in companies:
        data = CompanyPlacement.query.filter_by(user_id=current_user.id, company_name=company).first()
        if not data:
            data = CompanyPlacement(user_id=current_user.id, company_name=company,
                                    aptitude_score=random.randint(60,95), coding_score=random.randint(65,90), interview_score=random.randint(55,85))
            db.session.add(data)
            db.session.commit()
        data.overall_score = (data.aptitude_score + data.coding_score + data.interview_score) / 3
        company_data.append(data)
    return render_template('company_dashboard.html', companies=company_data)

# MODULE 10: ATS Resume Checker
@app.route('/ats_checker', methods=['GET','POST'])
@login_required
def ats_checker():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    result = None
    if analysis and analysis.resume_text:
        result = resume_optimizer.analyze_resume(analysis.resume_text, analysis.target_company or 'TCS')
    return render_template('ats_checker.html', result=result)

# MODULE 11: Job Recommendation Engine
@app.route('/job_recommendations')
@login_required
def job_recommendations():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    answers = AnswerEvaluation.query.filter_by(user_id=current_user.id).all()
    skills = json.loads(analysis.skills) if analysis and analysis.skills else []
    interview_scores = [a.score for a in answers if a.score]
    job_requirements = {
        'Software Engineer': {'skills': ['python','java','sql','data structures','algorithms'], 'min_score':60},
        'Data Analyst': {'skills': ['python','sql','excel','statistics','tableau'], 'min_score':60},
        'Python Developer': {'skills': ['python','django','flask','sql','rest api'], 'min_score':65},
        'ML Engineer': {'skills': ['python','machine learning','tensorflow','sql','statistics'], 'min_score':70},
        'Web Developer': {'skills': ['javascript','react','html','css','node.js'], 'min_score':60},
    }
    avg_interview = sum(interview_scores)/len(interview_scores) if interview_scores else 50
    skills_lower = [s.lower() for s in skills]
    recommendations = []
    for job, req in job_requirements.items():
        match = sum(1 for rs in req['skills'] if any(rs in us for us in skills_lower))
        skill_perc = (match/len(req['skills']))*100
        fit = (skill_perc*0.6)+(avg_interview*0.4)
        if fit >= req['min_score']:
            recommendations.append({'job_title':job,'fit_percentage':round(fit,1),'required_skills':req['skills'][:4],'skill_match':f"{match}/{len(req['skills'])}"})
    recommendations.sort(key=lambda x:x['fit_percentage'], reverse=True)
    return render_template('job_recommendations.html', recommendations=recommendations[:5])

# MODULE 12: AI HR Avatar Interview
@app.route('/avatar_interview')
@login_required
def avatar_interview():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    company = analysis.target_company if analysis else 'Company'
    role = analysis.job_role if analysis else 'Role'
    return render_template('avatar_interview.html', company=company, role=role)

# MODULE 13: Placement Analytics Dashboard
@app.route('/analytics_dashboard')
@login_required
def analytics_dashboard():
    answers = AnswerEvaluation.query.filter_by(user_id=current_user.id).all()
    weak_areas = WeakArea.query.filter_by(user_id=current_user.id).all()
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    scores = [a.score for a in answers if a.score]
    dates = [a.created_at.strftime('%Y-%m-%d') for a in answers]
    type_scores = {}
    for a in answers:
        q = InterviewQuestion.query.get(a.question_id)
        if q:
            type_scores.setdefault(q.question_type, []).append(a.score)
    avg_by_type = {k: sum(v)/len(v) for k,v in type_scores.items()}
    return render_template('analytics_dashboard.html', scores=scores, dates=dates,
                          avg_score=progress.average_score if progress else 0,
                          total_answers=len(answers), weak_areas=weak_areas[:5], type_scores=avg_by_type)

# MODULE 14: Group Discussion Module
@app.route('/group_discussion')
@login_required
def group_discussion():
    topics = ["Artificial Intelligence vs Human Intelligence - Which will dominate?",
              "Remote Work: The Future or a Temporary Trend?",
              "Social Media: Connecting People or Creating Divides?",
              "Cryptocurrency: Revolutionary or Risky Investment?",
              "Climate Change: Individual Responsibility vs Corporate Action"]
    return render_template('group_discussion.html', topics=topics)

@app.route('/evaluate_gd', methods=['POST'])
@login_required
def evaluate_gd():
    data = request.get_json()
    topic = data.get('topic', '')
    response = data.get('response', '')
    word_count = len(response.split())
    comm_score = 85 if word_count >= 100 else (65 if word_count >= 50 else 40)
    grammar_score = max(0, 100 - (response.lower().count('  ')*5))
    conf_score = min(100, (word_count/120)*100)
    overall = (comm_score*0.4)+(grammar_score*0.3)+(conf_score*0.3)
    gd = GroupDiscussion(user_id=current_user.id, topic=topic, user_response=response,
                         communication_score=comm_score, grammar_score=grammar_score,
                         confidence_score=conf_score, overall_score=overall)
    db.session.add(gd)
    db.session.commit()
    return jsonify({'communication_score':comm_score, 'grammar_score':grammar_score,
                    'confidence_score':conf_score, 'overall_score':round(overall,1),
                    'comm_feedback':'Good' if comm_score>60 else 'Needs improvement', 'word_count':word_count})

# MODULE 15: LinkedIn Profile Analyzer
@app.route('/linkedin_analyzer', methods=['GET','POST'])
@login_required
def linkedin_analyzer():
    result = None
    if request.method == 'POST':
        headline = request.form.get('headline','')
        skills = [s.strip() for s in request.form.get('skills','').split(',') if s.strip()]
        experience = [e.strip() for e in request.form.get('experience','').split(',') if e.strip()]
        headline_score = 100 if len(headline)>=60 else (70 if len(headline)>=30 else 40)
        skills_score = 100 if len(skills)>=10 else (60 if len(skills)>=5 else 30)
        exp_score = 100 if len(experience)>=2 else (50 if len(experience)>=1 else 20)
        overall = (headline_score+skills_score+exp_score)/3
        suggestions = []
        if headline_score<70: suggestions.append("Add a compelling headline with your key skills")
        if skills_score<60: suggestions.append(f"Add {10-len(skills)} more skills for better visibility")
        if exp_score<50: suggestions.append("Add detailed work experience descriptions")
        result = {'overall_score':round(overall,1), 'scores':{'headline':headline_score,'skills':skills_score,'experience':exp_score}, 'suggestions':suggestions}
    return render_template('linkedin_analyzer.html', result=result)

# MODULE 16: Placement Tracker
@app.route('/placement_tracker')
@login_required
def placement_tracker():
    apps = JobApplication.query.filter_by(user_id=current_user.id).order_by(JobApplication.application_date.desc()).all()
    stats = {'total':len(apps), 'applied':len([a for a in apps if a.status=='Applied']),
             'interview':len([a for a in apps if a.status=='Interview Scheduled']),
             'selected':len([a for a in apps if a.status=='Selected']),
             'rejected':len([a for a in apps if a.status=='Rejected'])}
    return render_template('placement_tracker.html', applications=apps, stats=stats)

@app.route('/add_application', methods=['POST'])
@login_required
def add_application():
    data = request.get_json()
    app = JobApplication(user_id=current_user.id, company_name=data.get('company'), job_role=data.get('role'), status=data.get('status','Applied'))
    db.session.add(app)
    db.session.commit()
    return jsonify({'status':'success'})

@app.route('/update_application/<int:app_id>', methods=['POST'])
@login_required
def update_application(app_id):
    app = JobApplication.query.get_or_404(app_id)
    if app.user_id != current_user.id:
        return jsonify({'error':'Unauthorized'}),403
    data = request.get_json()
    app.status = data.get('status')
    db.session.commit()
    return jsonify({'status':'success'})

# MODULE 17: Certificate Verification
@app.route('/certificates')
@login_required
def certificates():
    certs = Certificate.query.filter_by(user_id=current_user.id).all()
    return render_template('certificates.html', certificates=certs)

@app.route('/upload_certificate', methods=['POST'])
@login_required
def upload_certificate():
    name = request.form.get('name')
    authority = request.form.get('authority')
    category = request.form.get('category')
    if not category:
        if 'python' in name.lower(): category='Python'
        elif 'java' in name.lower(): category='Java'
        elif 'aws' in name.lower() or 'cloud' in name.lower(): category='AWS/Cloud'
        elif 'data' in name.lower(): category='Data Analytics'
        else: category='Other'
    cert = Certificate(user_id=current_user.id, certificate_name=name, issuing_authority=authority, category=category, verified=True)
    db.session.add(cert)
    db.session.commit()
    flash('Certificate uploaded!', 'success')
    return redirect(url_for('certificates'))

# MODULE 18: Career Path Predictor
@app.route('/career_predictor')
@login_required
def career_predictor():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    skills = json.loads(analysis.skills) if analysis and analysis.skills else []
    career_paths = {
        'Frontend Developer': ['html','css','javascript','react','angular'],
        'Backend Developer': ['python','java','node.js','sql','mongodb'],
        'Data Analyst': ['python','sql','excel','tableau','statistics'],
        'ML Engineer': ['python','machine learning','tensorflow','sql','statistics'],
        'DevOps Engineer': ['docker','kubernetes','aws','jenkins','linux']
    }
    skills_lower = [s.lower() for s in skills]
    predictions = []
    for career, req_skills in career_paths.items():
        match = sum(1 for rs in req_skills if any(rs in us for us in skills_lower))
        perc = (match/len(req_skills))*100
        predictions.append({'career':career, 'match_percentage':min(100,perc+10), 'required_skills':req_skills[:5]})
    predictions.sort(key=lambda x:x['match_percentage'], reverse=True)
    return render_template('career_predictor.html', predictions=predictions[:3])

# MODULE 19: Coding Contest Arena
@app.route('/coding_arena')
@login_required
def coding_arena():
    contests = [{'id':1,'name':'Weekly Challenge #1','difficulty':'Easy','participants':45,'top_score':95},
                {'id':2,'name':'Weekly Challenge #2','difficulty':'Medium','participants':32,'top_score':88},
                {'id':3,'name':'Weekly Challenge #3','difficulty':'Hard','participants':18,'top_score':76}]
    user_contests = CodingContest.query.filter_by(user_id=current_user.id).all()
    return render_template('coding_arena.html', contests=contests, user_contests=user_contests)

@app.route('/submit_contest/<int:contest_id>', methods=['POST'])
@login_required
def submit_contest(contest_id):
    data = request.get_json()
    code = data.get('code','')
    score = evaluate_code_quality(code)
    entry = CodingContest(contest_name=f'Weekly Challenge #{contest_id}', user_id=current_user.id, score=score)
    db.session.add(entry)
    db.session.commit()
    if score >= 90:
        award_badge(current_user.id, 'Coding Ninja', 'Coding')
    elif score >= 75:
        award_badge(current_user.id, 'Code Master', 'Coding')
    return jsonify({'score':score, 'message':'Submitted!'})

# MODULE 20: Placement Readiness Meter
@app.route('/readiness_meter')
@login_required
def readiness_meter():
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    weak_areas = WeakArea.query.filter_by(user_id=current_user.id).all()
    coding = min(100, (progress.total_questions_answered*2) if progress else 0)
    interview = progress.average_score*10 if progress else 0
    aptitude = random.randint(65,95)
    resume = 70
    if analysis and analysis.skills:
        skills_count = len(json.loads(analysis.skills))
        resume = min(100, 50 + (skills_count*2))
    overall = (coding+interview+aptitude+resume)/4 - (len(weak_areas)*3)
    overall = max(0, min(100, overall))
    readiness = {'overall':round(overall,1), 'coding':round(coding,1), 'interview':round(interview,1),
                 'aptitude':round(aptitude,1), 'resume':round(resume,1),
                 'level':'Excellent' if overall>=80 else 'Good' if overall>=60 else 'Needs Improvement'}
    return render_template('readiness_meter.html', readiness=readiness)

# MODULE 23: Company-Specific Resume Optimizer
@app.route('/resume_optimizer')
@login_required
def resume_optimizer_page():
    companies = ['TCS','Infosys','Wipro','Accenture','Cognizant','Google','Amazon','Microsoft','Meta','Adobe']
    return render_template('resume_optimizer.html', companies=companies)

@app.route('/analyze_company_resume', methods=['POST'])
@login_required
def analyze_company_resume():
    data = request.get_json()
    company = data.get('company')
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not analysis:
        return jsonify({'error':'Please upload your resume first'}),400
    result = resume_optimizer.analyze_resume(analysis.resume_text, company)
    result['suggestions'] = resume_optimizer.get_improvement_suggestions(result, company)
    return jsonify(result)

@app.route('/optimize_company_resume', methods=['POST'])
@login_required
def optimize_company_resume():
    data = request.get_json()
    company = data.get('company')
    rd = ResumeData.query.filter_by(user_id=current_user.id).first()
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not rd:
        return jsonify({'error':'Please build your resume first'}),400
    resume_data = {'summary':rd.summary or '', 'skills':json.loads(rd.skills) if rd.skills else [],
                   'projects':json.loads(rd.projects) if rd.projects else [], 'achievements':[]}
    resume_text = analysis.resume_text if analysis else ''
    analysis_result = resume_optimizer.analyze_resume(resume_text, company)
    optimized = resume_optimizer.generate_optimized_resume(resume_data, company, analysis_result)
    existing = CompanyResume.query.filter_by(user_id=current_user.id, company_name=company).first()
    if existing:
        existing.optimized_resume = json.dumps(optimized)
        existing.ats_score = analysis_result['ats_score']
        existing.readiness_score = analysis_result['readiness_score']
        existing.missing_skills = json.dumps(analysis_result['missing_skills'])
        existing.optimized_sections = json.dumps(optimized)
    else:
        cr = CompanyResume(user_id=current_user.id, company_name=company, optimized_resume=json.dumps(optimized),
                           ats_score=analysis_result['ats_score'], readiness_score=analysis_result['readiness_score'],
                           missing_skills=json.dumps(analysis_result['missing_skills']), optimized_sections=json.dumps(optimized))
        db.session.add(cr)
    db.session.commit()
    return jsonify({'analysis':analysis_result, 'optimized':optimized, 'message':f'Resume optimized for {company}!'})

@app.route('/compare_resume_companies')
@login_required
def compare_resume_companies():
    companies = ['TCS','Infosys','Google','Amazon','Microsoft','Wipro']
    rd = ResumeData.query.filter_by(user_id=current_user.id).first()
    analysis = ResumeAnalysis.query.filter_by(user_id=current_user.id).first()
    if not rd:
        return jsonify({'error':'Please build your resume first'}),400
    comparisons = []
    for comp in companies:
        if comp in resume_optimizer.company_requirements:
            resume_text = analysis.resume_text if analysis else ''
            res = resume_optimizer.analyze_resume(resume_text, comp)
            comparisons.append({'company':comp, 'ats_score':res['ats_score'], 'readiness_score':res['readiness_score'], 'meets_threshold':res['meets_threshold']})
    comparisons.sort(key=lambda x:x['ats_score'], reverse=True)
    return jsonify({'comparisons':comparisons})

@app.route('/save_resume_version', methods=['POST'])
@login_required
def save_resume_version():
    data = request.get_json()
    version = ResumeVersion(user_id=current_user.id, version_name=data.get('version_name'), resume_data=json.dumps(data.get('resume_data')))
    db.session.add(version)
    db.session.commit()
    return jsonify({'status':'success','version_id':version.id})

@app.route('/get_resume_versions')
@login_required
def get_resume_versions():
    versions = ResumeVersion.query.filter_by(user_id=current_user.id).order_by(ResumeVersion.created_at.desc()).all()
    return jsonify({'versions':[{'id':v.id,'name':v.version_name,'date':v.created_at.strftime('%Y-%m-%d %H:%M')} for v in versions]})

@app.route('/load_resume_version/<int:version_id>')
@login_required
def load_resume_version(version_id):
    version = ResumeVersion.query.get_or_404(version_id)
    if version.user_id != current_user.id:
        return jsonify({'error':'Unauthorized'}),403
    return jsonify({'resume_data':json.loads(version.resume_data)})

# ---------- MISSING API ROUTES (HR Generator, Concept Explainer, Coding Submit, Company Insights) ----------
@app.route('/hr_generator', methods=['POST'])
@login_required
def hr_generator():
    data = request.get_json()
    q = data.get('question','')
    ans = "Use STAR method. Be specific with metrics and examples."
    if 'yourself' in q.lower():
        ans = "I am a passionate professional with strong skills in development. I have experience building projects and I'm looking to grow at your company."
    elif 'strength' in q.lower():
        ans = "My greatest strength is problem-solving. For example, I optimized a system improving performance by 30%."
    elif 'weakness' in q.lower():
        ans = "I sometimes focus too much on details, but I've been working on this by setting time limits and prioritizing tasks."
    return jsonify({'answer':ans})

@app.route('/explain', methods=['POST'])
@login_required
def explain_concept():
    data = request.get_json()
    topic = data.get('topic','').lower()
    explanations = {
        'normalization':'Database normalization organizes data to reduce redundancy. Has normal forms: 1NF, 2NF, 3NF, BCNF.',
        'denormalization':'Denormalization adds redundancy to improve read performance.',
        'binary search':'Binary search finds an element in a sorted array in O(log n) time.',
        'array':'Array is a collection of elements at contiguous memory locations. Access O(1), insertion/deletion O(n).',
        'linked list':'Linked list is a linear data structure where elements are stored in nodes with pointers.',
        'stack':'Stack follows LIFO (Last In First Out) principle.',
        'queue':'Queue follows FIFO (First In First Out) principle.',
        'recursion':'Recursion is when a function calls itself. Must have base case and recursive case.',
        'dynamic programming':'DP solves problems by breaking them into overlapping subproblems and storing results.',
        'oop':'Object-Oriented Programming has four pillars: Encapsulation, Inheritance, Polymorphism, Abstraction.'
    }
    return jsonify({'explanation':explanations.get(topic, f"'{topic}' is an important concept. Practice implementing it.")})

@app.route('/coding/submit', methods=['POST'])
@login_required
def coding_submit():
    data = request.get_json()
    code = data.get('code','')
    passed = len(code.strip()) > 50
    score = 8 if passed else 4
    return jsonify({'passed':passed, 'score':score, 'message':'Accepted!' if passed else 'Needs improvement.'})

@app.route('/company_insights/<company_name>')
@login_required
def company_insights(company_name):
    insights = {
        'google':{'company_name':'Google','hiring_pattern':'Focus on algorithms, system design, and Googleyness','difficulty':'Very High','previous_questions':'Design YouTube, LRU Cache, Two Sum','salary_range':'₹30-60 LPA'},
        'amazon':{'company_name':'Amazon','hiring_pattern':'Leadership Principles focused, Bar Raiser system','difficulty':'High','previous_questions':'Design Amazon Locker, Implement LRU Cache','salary_range':'₹25-50 LPA'},
        'microsoft':{'company_name':'Microsoft','hiring_pattern':'Problem solving, system design, culture fit','difficulty':'High','previous_questions':'Design Bing, Implement autocomplete','salary_range':'₹25-45 LPA'},
        'tcs':{'company_name':'TCS','hiring_pattern':'Aptitude, coding, communication, HR round','difficulty':'Medium','previous_questions':'Basic programming, SQL queries','salary_range':'₹3-8 LPA'},
        'infosys':{'company_name':'Infosys','hiring_pattern':'Aptitude, technical, HR, system design','difficulty':'Medium','previous_questions':'OOPS concepts, DBMS, algorithms','salary_range':'₹3-8 LPA'}
    }
    insight = insights.get(company_name.lower(), {'company_name':company_name, 'hiring_pattern':'Technical + HR rounds', 'difficulty':'Medium', 'previous_questions':'Data structures, Algorithms, Behavioral', 'salary_range':'Varies by role'})
    return render_template('company_insights.html', insight=insight)

@app.route('/set_company_session', methods=['POST'])
@login_required
def set_company_session():
    data = request.get_json()
    session['company'] = data.get('company')
    return jsonify({'status':'ok'})

@app.route('/set_job_role', methods=['POST'])
@login_required
def set_job_role():
    data = request.get_json()
    session['role'] = data.get('role')
    return jsonify({'status':'ok'})

# ---------- DATABASE CLEANUP ----------
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# ---------- RUN ----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5500)