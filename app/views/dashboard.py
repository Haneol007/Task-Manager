from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.project import Project
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard with charts and statistics"""
    return render_template('dashboard/analytics.html')

@dashboard_bp.route('/api/task-completion-chart')
@login_required
def task_completion_chart():
    """API endpoint for task completion over time chart"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily task completion data
    daily_completions = db.session.query(
        func.date(Task.completed_at).label('date'),
        func.count(Task.id).label('count')
    ).filter(
        Task.user_id == current_user.id,
        Task.completed_at >= start_date,
        Task.is_completed == True
    ).group_by(func.date(Task.completed_at)).all()
    
    # Create date range and fill gaps
    chart_data = {}
    current_date = start_date.date()
    end_date = datetime.utcnow().date()
    
    while current_date <= end_date:
        chart_data[current_date.isoformat()] = 0
        current_date += timedelta(days=1)
    
    # Fill in actual data
    for date, count in daily_completions:
        chart_data[date.isoformat()] = count
    
    return jsonify({
        'labels': list(chart_data.keys()),
        'data': list(chart_data.values())
    })

@dashboard_bp.route('/api/priority-distribution')
@login_required
def priority_distribution():
    """API endpoint for task priority distribution chart"""
    priority_counts = db.session.query(
        Task.priority,
        func.count(Task.id).label('count')
    ).filter(
        Task.user_id == current_user.id,
        Task.is_completed == False
    ).group_by(Task.priority).all()
    
    priority_data = {priority.value: 0 for priority in TaskPriority}
    
    for priority, count in priority_counts:
        if priority:
            priority_data[priority.value] = count
    
    return jsonify({
        'labels': [priority.title() for priority in priority_data.keys()],
        'data': list(priority_data.values()),
        'colors': ['#28a745', '#ffc107', '#fd7e14', '#dc3545']  # Low, Medium, High, Urgent
    })

@dashboard_bp.route('/api/project-progress')
@login_required
def project_progress():
    """API endpoint for project progress data"""
    projects = Project.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    project_data = []
    for project in projects:
        stats = project.get_task_stats()
        project_data.append({
            'name': project.name,
            'completion_rate': stats['completion_rate'],
            'total_tasks': stats['total_tasks'],
            'completed_tasks': stats['completed_tasks'],
            'color': project.color
        })
    
    return jsonify(project_data)

@dashboard_bp.route('/api/weekly-activity')
@login_required
def weekly_activity():
    """API endpoint for weekly task activity heatmap"""
    # Get task activity for the last 8 weeks
    start_date = datetime.utcnow() - timedelta(weeks=8)
    
    tasks_created = db.session.query(
        func.date(Task.created_at).label('date'),
        func.count(Task.id).label('count')
    ).filter(
        Task.user_id == current_user.id,
        Task.created_at >= start_date
    ).group_by(func.date(Task.created_at)).all()
    
    tasks_completed = db.session.query(
        func.date(Task.completed_at).label('date'),
        func.count(Task.id).label('count')
    ).filter(
        Task.user_id == current_user.id,
        Task.completed_at >= start_date,
        Task.is_completed == True
    ).group_by(func.date(Task.completed_at)).all()
    
    # Process data into weekly format
    weekly_data = []
    current_date = start_date.date()
    end_date = datetime.utcnow().date()
    
    created_dict = {date.isoformat(): count for date, count in tasks_created}
    completed_dict = {date.isoformat(): count for date, count in tasks_completed}
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        weekly_data.append({
            'date': date_str,
            'day': current_date.strftime('%A'),
            'week': current_date.isocalendar()[1],
            'created': created_dict.get(date_str, 0),
            'completed': completed_dict.get(date_str, 0)
        })
        current_date += timedelta(days=1)
    
    return jsonify(weekly_data)

@dashboard_bp.route('/api/overdue-tasks')
@login_required
def overdue_tasks():
    """API endpoint for overdue tasks data"""
    overdue_tasks = Task.query.filter(
        and_(
            Task.user_id == current_user.id,
            Task.due_date < datetime.utcnow(),
            Task.is_completed == False
        )
    ).order_by(Task.due_date.asc()).limit(10).all()
    
    return jsonify([{
        'id': task.id,
        'title': task.title,
        'due_date': task.due_date.isoformat(),
        'days_overdue': (datetime.utcnow() - task.due_date).days,
        'priority': task.priority.value if task.priority else 'medium',
        'priority_label': task.get_priority_label()
    } for task in overdue_tasks])

@dashboard_bp.route('/api/productivity-stats')
@login_required
def productivity_stats():
    """API endpoint for productivity statistics"""
    now = datetime.utcnow()
    
    # This week vs last week
    this_week_start = now - timedelta(days=now.weekday())
    last_week_start = this_week_start - timedelta(weeks=1)
    last_week_end = this_week_start
    
    this_week_completed = Task.query.filter(
        Task.user_id == current_user.id,
        Task.completed_at >= this_week_start,
        Task.is_completed == True
    ).count()
    
    last_week_completed = Task.query.filter(
        Task.user_id == current_user.id,
        Task.completed_at >= last_week_start,
        Task.completed_at < last_week_end,
        Task.is_completed == True
    ).count()
    
    # This month vs last month
    this_month_start = now.replace(day=1)
    if this_month_start.month == 1:
        last_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12)
    else:
        last_month_start = this_month_start.replace(month=this_month_start.month - 1)
    
    this_month_completed = Task.query.filter(
        Task.user_id == current_user.id,
        Task.completed_at >= this_month_start,
        Task.is_completed == True
    ).count()
    
    last_month_completed = Task.query.filter(
        Task.user_id == current_user.id,
        Task.completed_at >= last_month_start,
        Task.completed_at < this_month_start,
        Task.is_completed == True
    ).count()
    
    # Calculate percentage changes
    week_change = ((this_week_completed - last_week_completed) / last_week_completed * 100) if last_week_completed > 0 else 0
    month_change = ((this_month_completed - last_month_completed) / last_month_completed * 100) if last_month_completed > 0 else 0
    
    # Average completion time
    completed_tasks_with_time = Task.query.filter(
        Task.user_id == current_user.id,
        Task.is_completed == True,
        Task.completed_at.isnot(None),
        Task.created_at.isnot(None)
    ).all()
    
    if completed_tasks_with_time:
        total_duration = sum(
            (task.completed_at - task.created_at).total_seconds() 
            for task in completed_tasks_with_time
        )
        avg_completion_hours = total_duration / len(completed_tasks_with_time) / 3600
    else:
        avg_completion_hours = 0
    
    return jsonify({
        'this_week_completed': this_week_completed,
        'last_week_completed': last_week_completed,
        'week_change_percentage': round(week_change, 1),
        'this_month_completed': this_month_completed,
        'last_month_completed': last_month_completed,
        'month_change_percentage': round(month_change, 1),
        'average_completion_hours': round(avg_completion_hours, 2)
    })

@dashboard_bp.route('/api/task-categories')
@login_required
def task_categories():
    """API endpoint for task categories distribution"""
    categories = db.session.query(
        Task.category,
        func.count(Task.id).label('count')
    ).filter(
        Task.user_id == current_user.id,
        Task.category.isnot(None),
        Task.category != ''
    ).group_by(Task.category).order_by(func.count(Task.id).desc()).limit(10).all()
    
    return jsonify([{
        'category': category or 'Uncategorized',
        'count': count
    } for category, count in categories])