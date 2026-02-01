from sqlalchemy.orm import Session
from sqlalchemy import text
from .models import Question, AnswerOption, QuizAttempt, AttemptAnswer

def create_question(db: Session, category: str, text: str):
    q = Question(category=category, text=text)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q

def add_option(db: Session, question_id: int, text: str, is_correct: bool):
    opt = AnswerOption(question_id=question_id, text=text, is_correct=is_correct)
    db.add(opt)
    db.commit()
    db.refresh(opt)
    return opt

def list_questions(db: Session):
    return db.query(Question).order_by(Question.id.asc()).all()

def get_options_for_question(db: Session, question_id: int):
    return db.query(AnswerOption).filter(AnswerOption.question_id == question_id).all()

def start_attempt(db: Session, user_id: int) -> QuizAttempt:
    a = QuizAttempt(user_id=user_id, score=0, total=0)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a

def submit_attempt(db: Session, attempt_id: int, answers: list[dict]) -> QuizAttempt:
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    if not attempt:
        raise ValueError("Attempt not found")

    score = 0
    total = len(answers)

    # clear previous attempt answers (optional)
    db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt_id).delete()

    for a in answers:
        opt = db.query(AnswerOption).filter(AnswerOption.id == a["selected_option_id"]).first()
        is_correct = bool(opt and opt.is_correct)
        if is_correct:
            score += 1
        db.add(AttemptAnswer(
            attempt_id=attempt_id,
            question_id=a["question_id"],
            selected_option_id=a["selected_option_id"],
            is_correct=is_correct
        ))

    attempt.score = score
    attempt.total = total
    db.commit()
    db.refresh(attempt)
    return attempt

def category_breakdown(db: Session, attempt_id: int) -> dict:
    # compute correct counts per category
    rows = db.execute(
        text("""
        SELECT q.category, SUM(CASE WHEN aa.is_correct THEN 1 ELSE 0 END) AS correct
        FROM attempt_answer aa
        JOIN question q ON q.id = aa.question_id
        WHERE aa.attempt_id = :aid
        GROUP BY q.category
        """),
        {"aid": attempt_id},
    ).fetchall()

    out = {"logic": 0, "programming": 0, "networking": 0, "design": 0}
    for cat, correct in rows:
        if cat in out:
            out[cat] = int(correct or 0)
    return out
