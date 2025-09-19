from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.task import Task
from app.models.project import Project
from datetime import datetime, timedelta
from sqlalchemy import and_

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page - redirect to dashboard if logged in"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with task overview"""
    # Get recent tasks
    recent_tasks = Task.query.filter_by(user_id=current_user.id)\
        .order_by(Task.updated_at.desc())\
        .limit(5).all()
    
    # Get overdue tasks
    overdue_tasks = Task.query.filter(
        and_(
            Task.user_id == current_user.id,
            Task.due_date < datetime.utcnow(),
            Task.is_completed == False
        )
    ).limit(5).all()
    
    # Get upcoming tasks (due in next 7 days)
    week_end = datetime.utcnow() + timedelta(days=7)
    upcoming_tasks = Task.query.filter(
        and_(
            Task.user_id == current_user.id,
            Task.due_date.between(datetime.utcnow(), week_end),
            Task.is_completed == False
        )
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Get active projects
    active_projects = Project.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).limit(5).all()
    
    # Calculate statistics
    stats = current_user.get_task_stats()
    
    return render_template('dashboard.html',
                         recent_tasks=recent_tasks,
                         overdue_tasks=overdue_tasks,
                         upcoming_tasks=upcoming_tasks,
                         active_projects=active_projects,
                         stats=stats)

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_bp.route('/help')
def help():
    """Help/documentation page"""
    return render_template('help.html')