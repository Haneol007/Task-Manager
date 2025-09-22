from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.task import Task, TaskPriority, TaskStatus, TaskComment
from app.models.project import Project
from datetime import datetime, timedelta
from sqlalchemy import or_, and_

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/')
@login_required
def list_tasks():
    """List all tasks for the current user"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    search = request.args.get('search', '')
    project_id = request.args.get('project', type=int)
    
    # Build query
    query = Task.query.filter_by(user_id=current_user.id, parent_task_id=None)
    
    if status_filter:
        if status_filter == 'completed':
            query = query.filter_by(is_completed=True)
        elif status_filter == 'pending':
            query = query.filter_by(is_completed=False)
        else:
            query = query.filter(Task.status == TaskStatus(status_filter))
    
    if priority_filter:
        query = query.filter(Task.priority == TaskPriority(priority_filter))
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term),
                Task.tags.ilike(search_term)
            )
        )
    
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    # Order by priority and due date
    query = query.order_by(
        Task.is_completed.asc(),
        Task.priority.desc(),
        Task.due_date.asc().nullslast(),
        Task.created_at.desc()
    )
    
    tasks = query.paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Get user's projects for filter dropdown
    projects = Project.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    return render_template('tasks/list.html', 
                         tasks=tasks, 
                         projects=projects,
                         current_filters={
                             'status': status_filter,
                             'priority': priority_filter,
                             'search': search,
                             'project': project_id
                         })

@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """Create a new task"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date', '')
        estimated_hours = request.form.get('estimated_hours', 0, type=float)
        tags = request.form.get('tags', '').strip()
        category = request.form.get('category', '').strip()
        project_id = request.form.get('project_id', type=int)
        parent_task_id = request.form.get('parent_task_id', type=int)
        
        if not title:
            flash('Task title is required', 'error')
            return render_template('tasks/create.html')
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid due date format', 'error')
                return render_template('tasks/create.html')
        
        try:
            task = Task(
                title=title,
                description=description,
                user_id=current_user.id,
                priority=TaskPriority(priority),
                due_date=due_date
            )
            
            task.estimated_hours = estimated_hours
            task.category = category
            task.project_id = project_id if project_id else None
            task.parent_task_id = parent_task_id if parent_task_id else None
            
            # Set tags
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                task.set_tags(tag_list)
            
            db.session.add(task)
            db.session.commit()
            
            flash('Task created successfully!', 'success')
            return redirect(url_for('tasks.view_task', id=task.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the task', 'error')
    
    # Get user's projects and tasks for parent task selection
    projects = Project.query.filter_by(user_id=current_user.id, is_active=True).all()
    parent_tasks = Task.query.filter_by(user_id=current_user.id, parent_task_id=None).all()
    
    return render_template('tasks/create.html', projects=projects, parent_tasks=parent_tasks)

@tasks_bp.route('/<int:id>')
@login_required
def view_task(id):
    """View a specific task"""
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    comments = task.comments.order_by(TaskComment.created_at.desc()).all()
    subtasks = task.subtasks.order_by(Task.created_at.asc()).all()
    
    return render_template('tasks/view.html', task=task, comments=comments, subtasks=subtasks)

@tasks_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    """Edit an existing task"""
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        task.title = request.form.get('title', '').strip()
        task.description = request.form.get('description', '').strip()
        task.priority = TaskPriority(request.form.get('priority', 'medium'))
        task.status = TaskStatus(request.form.get('status', 'todo'))
        
        due_date_str = request.form.get('due_date', '')
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                task.due_date = None
        else:
            task.due_date = None
        
        task.estimated_hours = request.form.get('estimated_hours', 0, type=float)
        task.actual_hours = request.form.get('actual_hours', 0, type=float)
        task.category = request.form.get('category', '').strip()
        task.project_id = request.form.get('project_id', type=int) or None
        
        # Handle tags
        tags = request.form.get('tags', '').strip()
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            task.set_tags(tag_list)
        else:
            task.tags = ''
        
        if not task.title:
            flash('Task title is required', 'error')
            return render_template('tasks/edit.html', task=task)
        
        try:
            task.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Task updated successfully!', 'success')
            return redirect(url_for('tasks.view_task', id=task.id))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the task', 'error')
    
    # Get user's projects for dropdown
    projects = Project.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    return render_template('tasks/edit.html', task=task, projects=projects)

@tasks_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_task(id):
    """Delete a task - FIXED VERSION"""
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        # PROPER CASCADE DELETION:
        
        # 1. Handle subtasks - either delete them or make them independent
        subtasks = Task.query.filter_by(parent_task_id=task.id).all()
        for subtask in subtasks:
            subtask.parent_task_id = None  # Make subtasks independent
            # OR: db.session.delete(subtask)  # Delete subtasks too
        
        # 2. Delete related comments
        for comment in task.comments:
            db.session.delete(comment)
        
        # 3. Delete related attachments
        for attachment in task.attachments:
            db.session.delete(attachment)
        
        # 4. Finally delete the main task
        db.session.delete(task)
        db.session.commit()
        
        flash('Task deleted successfully!', 'success')
        return redirect(url_for('tasks.list_tasks'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the task. Please try again.', 'error')
        return redirect(url_for('tasks.view_task', id=id))

@tasks_bp.route('/<int:id>/toggle-complete', methods=['POST'])
@login_required
def toggle_complete(id):
    """Toggle task completion status"""
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        if task.is_completed:
            task.mark_incomplete()
        else:
            task.mark_completed()
        
        db.session.commit()
        
        status = 'completed' if task.is_completed else 'marked as incomplete'
        flash(f'Task {status}!', 'success')
        
        # Return JSON response for AJAX requests
        if request.is_json:
            return jsonify({
                'success': True,
                'is_completed': task.is_completed,
                'status_label': task.get_status_label()
            })
        
        return redirect(url_for('tasks.view_task', id=id))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating the task', 'error')
        
        if request.is_json:
            return jsonify({'success': False, 'error': 'Database error'}), 500
        
        return redirect(url_for('tasks.view_task', id=id))

@tasks_bp.route('/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    """Add a comment to a task"""
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    content = request.form.get('content', '').strip()
    
    if not content:
        flash('Comment cannot be empty', 'error')
        return redirect(url_for('tasks.view_task', id=id))
    
    try:
        comment = TaskComment(
            content=content,
            task_id=task.id,
            user_id=current_user.id
        )
        db.session.add(comment)
        db.session.commit()
        
        flash('Comment added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while adding the comment', 'error')
    
    return redirect(url_for('tasks.view_task', id=id))

@tasks_bp.route('/dashboard-stats')
@login_required
def dashboard_stats():
    """Get task statistics for dashboard"""
    total_tasks = Task.query.filter_by(user_id=current_user.id).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, is_completed=True).count()
    pending_tasks = total_tasks - completed_tasks
    overdue_tasks = Task.query.filter(
        and_(
            Task.user_id == current_user.id,
            Task.due_date < datetime.utcnow(),
            Task.is_completed == False
        )
    ).count()
    
    # Tasks due this week
    week_end = datetime.utcnow() + timedelta(days=7)
    due_this_week = Task.query.filter(
        and_(
            Task.user_id == current_user.id,
            Task.due_date.between(datetime.utcnow(), week_end),
            Task.is_completed == False
        )
    ).count()
    
    return jsonify({
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'overdue_tasks': overdue_tasks,
        'due_this_week': due_this_week,
        'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
    })
