from app import db
from datetime import datetime, timedelta
from sqlalchemy import event
from enum import Enum

class TaskPriority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'

class TaskStatus(Enum):
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    REVIEW = 'review'
    DONE = 'done'

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.TODO)
    is_completed = db.Column(db.Boolean, default=False, index=True)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime, index=True)
    completed_at = db.Column(db.DateTime)
    
    # Estimated and actual time tracking
    estimated_hours = db.Column(db.Float, default=0)
    actual_hours = db.Column(db.Float, default=0)
    
    # Tags and categorization
    tags = db.Column(db.String(500))  # Comma-separated tags
    category = db.Column(db.String(100))
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), index=True)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), index=True)
    
    # Relationships
    comments = db.relationship('TaskComment', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    subtasks = db.relationship('Task', backref=db.backref('parent_task', remote_side=[id]), lazy='dynamic')
    attachments = db.relationship('TaskAttachment', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, title, description=None, user_id=None, priority=TaskPriority.MEDIUM, due_date=None):
        self.title = title
        self.description = description
        self.user_id = user_id
        self.priority = priority
        self.due_date = due_date
    
    def mark_completed(self):
        """Mark task as completed"""
        self.is_completed = True
        self.status = TaskStatus.DONE
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Also mark all subtasks as completed
        for subtask in self.subtasks:
            if not subtask.is_completed:
                subtask.mark_completed()
    
    def mark_incomplete(self):
        """Mark task as incomplete"""
        self.is_completed = False
        self.status = TaskStatus.TODO
        self.completed_at = None
        self.updated_at = datetime.utcnow()
    
    def is_overdue(self):
        """Check if task is overdue"""
        return (self.due_date and 
                self.due_date < datetime.utcnow() and 
                not self.is_completed)
    
    def days_until_due(self):
        """Calculate days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.utcnow()
        return delta.days
    
    def get_priority_label(self):
        """Get human-readable priority label"""
        priority_labels = {
            TaskPriority.LOW: 'Low',
            TaskPriority.MEDIUM: 'Medium',
            TaskPriority.HIGH: 'High',
            TaskPriority.URGENT: 'Urgent'
        }
        return priority_labels.get(self.priority, 'Medium')
    
    def get_status_label(self):
        """Get human-readable status label"""
        status_labels = {
            TaskStatus.TODO: 'To Do',
            TaskStatus.IN_PROGRESS: 'In Progress',
            TaskStatus.REVIEW: 'Review',
            TaskStatus.DONE: 'Done'
        }
        return status_labels.get(self.status, 'To Do')
    
    def get_tags_list(self):
        """Get tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def set_tags(self, tags_list):
        """Set tags from a list"""
        if tags_list:
            self.tags = ','.join([tag.strip() for tag in tags_list if tag.strip()])
        else:
            self.tags = ''
    
    def get_progress_percentage(self):
        """Calculate task progress based on subtasks"""
        if not self.subtasks.count():
            return 100 if self.is_completed else 0
        
        total_subtasks = self.subtasks.count()
        completed_subtasks = self.subtasks.filter_by(is_completed=True).count()
        return int((completed_subtasks / total_subtasks) * 100)
    
    def to_dict(self, include_subtasks=False):
        """Convert task to dictionary for API responses"""
        task_dict = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value if self.priority else 'medium',
            'priority_label': self.get_priority_label(),
            'status': self.status.value if self.status else 'todo',
            'status_label': self.get_status_label(),
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'tags': self.get_tags_list(),
            'category': self.category,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'parent_task_id': self.parent_task_id,
            'is_overdue': self.is_overdue(),
            'days_until_due': self.days_until_due(),
            'progress_percentage': self.get_progress_percentage(),
            'comments_count': self.comments.count(),
            'subtasks_count': self.subtasks.count()
        }
        
        if include_subtasks:
            task_dict['subtasks'] = [subtask.to_dict() for subtask in self.subtasks]
        
        return task_dict
    
    def __repr__(self):
        return f'<Task {self.title}>'


class TaskComment(db.Model):
    __tablename__ = 'task_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'author_name': self.author.get_full_name() if self.author else 'Unknown'
        }


class TaskAttachment(db.Model):
    __tablename__ = 'task_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    upload_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'created_at': self.created_at.isoformat(),
            'task_id': self.task_id,
            'uploaded_by': self.uploaded_by
        }


# Event listeners for automatic task updates
@event.listens_for(Task.is_completed, 'set')
def task_completion_listener(target, value, oldvalue, initiator):
    """Auto-update completion timestamp when task is marked complete"""
    if value and not oldvalue:
        target.completed_at = datetime.utcnow()
        target.status = TaskStatus.DONE
    elif not value and oldvalue:
        target.completed_at = None
        target.status = TaskStatus.TODO