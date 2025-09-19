from app import db
from datetime import datetime

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')  # Hex color code
    is_active = db.Column(db.Boolean, default=True)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    tasks = db.relationship('Task', backref='project', lazy='dynamic')
    
    def __init__(self, name, description=None, user_id=None, color='#007bff'):
        self.name = name
        self.description = description
        self.user_id = user_id
        self.color = color
    
    def get_task_stats(self):
        """Get project task statistics"""
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
    
    def is_overdue(self):
        """Check if project is overdue"""
        return (self.end_date and 
                self.end_date < datetime.utcnow() and 
                not self.is_completed())
    
    def is_completed(self):
        """Check if all project tasks are completed"""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return False
        completed_tasks = self.tasks.filter_by(is_completed=True).count()
        return total_tasks == completed_tasks
    
    def to_dict(self):
        """Convert project to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'user_id': self.user_id,
            'is_overdue': self.is_overdue(),
            'is_completed': self.is_completed(),
            'task_stats': self.get_task_stats()
        }
    
    def __repr__(self):
        return f'<Project {self.name}>'