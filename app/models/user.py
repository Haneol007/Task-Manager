from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import hashlib

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    avatar_url = db.Column(db.String(200))
    bio = db.Column(db.Text)
    
    # Relationships
    tasks = db.relationship('Task', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    projects = db.relationship('Project', backref='owner', lazy='dynamic')
    task_comments = db.relationship('TaskComment', backref='author', lazy='dynamic')
    
    def __init__(self, username, email, password, first_name, last_name):
        self.username = username
        self.email = email
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.avatar_url = self.get_avatar_url()
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_avatar_url(self, size=128):
        """Generate gravatar URL"""
        digest = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
    
    def get_full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_task_stats(self):
        """Get user's task statistics"""
        total_tasks = self.tasks.count()
        completed_tasks = self.tasks.filter_by(is_completed=True).count()
        pending_tasks = total_tasks - completed_tasks
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'completion_rate': round(completion_rate, 2)
        }
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'task_stats': self.get_task_stats()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'