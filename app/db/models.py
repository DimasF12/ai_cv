from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    domain = Column(String, nullable=True)
    logo = Column(String, nullable=True)
    settings = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default='active')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    email_verified_at = Column(DateTime, nullable=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False, default='active')
    avatar_initials = Column(String, nullable=True)
    avatar_color = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    title = Column(String, nullable=True)
    remember_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    email_verified_at = Column(DateTime, nullable=True)
    password = Column(String, nullable=False)
    status = Column(String, nullable=False, default='active')
    avatar_initials = Column(String, nullable=True)
    avatar_color = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    title = Column(String, nullable=True)
    location = Column(String, nullable=True)
    about = Column(Text, nullable=True)
    skills = Column(JSON, nullable=True)
    linkedin = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    education = Column(String, nullable=True)
    experience_years = Column(Integer, nullable=True)
    preferred_location_type = Column(String, nullable=True)
    preferred_job_type = Column(String, nullable=True)
    remember_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

class EmployeeCV(Base):
    __tablename__ = "employee_cvs"

    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    size = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    location = Column(String, nullable=False)
    location_type = Column(String, nullable=False, default='on-site')
    department = Column(String, nullable=False)
    type = Column(String, nullable=False, default='full-time')
    experience_level = Column(String, nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String, nullable=False, default='IDR')
    openings = Column(Integer, nullable=False, default=1)
    education_requirement = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)
    benefits = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='draft')
    company = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    applicant_count = Column(Integer, nullable=False, default=0)
    unseen_applicant_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

class Applicant(Base):
    __tablename__ = "applicants"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    status = Column(String, nullable=False, default='pending_analysis')
    skills_match_score = Column(Integer, nullable=True)
    experience_score = Column(Integer, nullable=True)
    education_score = Column(Integer, nullable=True)
    overall_score = Column(Integer, nullable=True)
    cv_summary = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    exam_status = Column(String, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    cv_id = Column(String, nullable=True)

class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    category = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct_answer = Column(String, nullable=False)
    difficulty = Column(String, nullable=False, default='medium')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Exam(Base):
    __tablename__ = "exams"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    applicant_id = Column(String, ForeignKey("applicants.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    question_ids = Column(JSON, nullable=True)
    answers = Column(JSON, nullable=True)
    score = Column(Integer, nullable=True)
    passed = Column(Boolean, nullable=True)
    correct_count = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=False, default=10)
    total_time_seconds = Column(Integer, nullable=False, default=1800)
    time_spent_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    focus_lost_count = Column(Integer, nullable=False, default=0)
    max_focus_loss = Column(Integer, nullable=False, default=3)
    status = Column(String, nullable=False, default='pending')
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class RecruitmentProcessStep(Base):
    __tablename__ = "recruitment_process_steps"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    color = Column(String, nullable=True)
    order = Column(Integer, nullable=False, default=1)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
