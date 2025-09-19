from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.project import Project
from datetime import datetime
from functools import wraps

api_bp = Blueprint('api', __name__)

def api_response(data=None, message=None, status=200, success=True):
    """Standardized API response format"""
    response = {
        'success': success,
        'message': message,
        'data': data
    }
    return jsonify(response), status

def validate_json(required_fields):
    """Decorator to validate required JSON fields"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return api_response(message="Content-Type must be application/json", status=400, success=False)
            
            data = request.get_json()
            missing_fields = [field for field in required_fields if field not in data or not data[field]]
            
            if missing_fields:
                return api_response(
                    message=f"Missing required fields: {', '.join(missing_fields)}", 
                    status=400, 
                    success=False
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Task API endpoints
@api_bp.route('/tasks', methods=['GET'])
@login_required
def api_get_tasks():
    """Get all tasks for the current user"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    project_id = request.args.get('project_id', type=int)
    include_subtasks = request.args.get('include_subtasks', 'false').lower() == 'true'
    
    query = Task.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if status_filter == 'completed':
        query = query.filter_by(is_completed=True)
    elif status_filter == 'pending':
        query = query.filter_by(is_completed=False)
    elif status_filter and status_filter in [s.value for s in TaskStatus]:
        query = query.filter(Task.status == TaskStatus(status_filter))
    
    if priority_filter and priority_filter in [p.value for p in TaskPriority]:
        query = query.filter(Task.priority == TaskPriority(priority_filter))
    
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    # Pagination
    tasks_pagination = query.order_by(Task.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    tasks_data = [task.to_dict(include_subtasks=include_subtasks) for task in tasks_pagination.items]
    
    return api_response(data={
        'tasks': tasks_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': tasks_pagination.total,
            'pages': tasks_pagination.pages,
            'has_next': tasks_pagination.has_next,
            'has_prev': tasks_pagination.has_prev
        }
    })

@api_bp.route('/tasks', methods=['POST'])
@login_required
@validate_json(['title'])
def api_create_task():
    """Create a new task"""
    data = request.get_json()
    
    try:
        # Parse due date if provided
        due_date = None
        if data.get('due_date'):
            due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
        
        task = Task(
            title=data['title'],
            description=data.get('description', ''),
            user_id=current_user.id,
            priority=TaskPriority(data.get('priority', 'medium')),
            due_date=due_date
        )
        
        # Optional fields
        if data.get('estimated_hours'):
            task.estimated_hours = float(data['estimated_hours'])
        if data.get('category'):
            task.category = data['category']
        if data.get('project_id'):
            task.project_id = data['project_id']
        if data.get('parent_task_id'):
            task.parent_task_id = data['parent_task_id']
        if data.get('tags'):
            task.set_tags(data['tags'])
        
        db.session.add(task)
        db.session.commit()
        
        return api_response(
            data=task.to_dict(),
            message="Task created successfully",
            status=201
        )
        
    except ValueError as e:
        return api_response(message=str(e), status=400, success=False)
    except Exception as e:
        db.session.rollback()
        return api_response(message="Failed to create task", status=500, success=False)

@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def api_get_task(task_id):
    """Get a specific task"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    
    if not task:
        return api_response(message="Task not found", status=404, success=False)
    
    include_subtasks = request.args.get('include_subtasks', 'false').lower() == 'true'
    return api_response(data=task.to_dict(include_subtasks=include_subtasks))

@api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def api_update_task(task_id):
    """Update a specific task"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    
    if not task:
        return api_response(message="Task not found", status=404, success=False)
    
    data = request.get_json()
    if not data:
        return api_response(message="No data provided", status=400, success=False)
    
    try:
        # Update fields if provided
        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'priority' in data:
            task.priority = TaskPriority(data['priority'])
        if 'status' in data:
            task.status = TaskStatus(data['status'])
        if 'is_completed' in data:
            task.is_completed = bool(data['is_completed'])
        if 'estimated_hours' in data:
            task.estimated_hours = float(data['estimated_hours'])
        if 'actual_hours' in data:
            task.actual_hours = float(data['actual_hours'])
        if 'category' in data:
            task.category = data['category']
        if 'project_id' in data:
            task.project_id = data['project_id']
        if 'tags' in data:
            task.set_tags(data['tags'])
        if 'due_date' in data:
            if data['due_date']:
                task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            else:
                task.due_date = None
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        return api_response(
            data=task.to_dict(),
            message="Task updated successfully"
        )
        
    except ValueError as e:
        return api_response(message=str(e), status=400, success=False)
    except Exception as e:
        db.session.rollback()
        return api_response(message="Failed to update task", status=500, success=False)

@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def api_delete_task(task_id):
    """Delete a specific task"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    
    if not task:
        return api_response(message="Task not found", status=404, success=False)
    
    try:
        # Same intentional bug as in the web interface
        db.session.delete(task)
        db.session.commit()
        
        return api_response(message="Task deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        return api_response(message="Failed to delete task", status=500, success=False)

# Project API endpoints
@api_bp.route('/projects', methods=['GET'])
@login_required
def api_get_projects():
    """Get all projects for the current user"""
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return api_response(data=[project.to_dict() for project in projects])

@api_bp.route('/projects', methods=['POST'])
@login_required
@validate_json(['name'])
def api_create_project():
    """Create a new project"""
    data = request.get_json()
    
    try:
        project = Project(
            name=data['name'],
            description=data.get('description', ''),
            user_id=current_user.id,
            color=data.get('color', '#007bff')
        )
        
        if data.get('start_date'):
            project.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        if data.get('end_date'):
            project.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        
        db.session.add(project)
        db.session.commit()
        
        return api_response(
            data=project.to_dict(),
            message="Project created successfully",
            status=201
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(message="Failed to create project", status=500, success=False)

# Statistics API endpoint
@api_bp.route('/stats', methods=['GET'])
@login_required
def api_get_stats():
    """Get user statistics"""
    user_stats = current_user.get_task_stats()
    
    # Get project stats
    projects = Project.query.filter_by(user_id=current_user.id).all()
    project_stats = []
    
    for project in projects:
        project_stats.append({
            'project': project.to_dict(),
            'task_stats': project.get_task_stats()
        })
    
    return api_response(data={
        'user_stats': user_stats,
        'project_stats': project_stats,
        'total_projects': len(projects),
        'active_projects': len([p for p in projects if p.is_active])
    })

# Error handlers for API
@api_bp.errorhandler(400)
def api_bad_request(error):
    return api_response(message="Bad request", status=400, success=False)

@api_bp.errorhandler(401)
def api_unauthorized(error):
    return api_response(message="Unauthorized", status=401, success=False)

@api_bp.errorhandler(403)
def api_forbidden(error):
    return api_response(message="Forbidden", status=403, success=False)

@api_bp.errorhandler(404)
def api_not_found(error):
    return api_response(message="Resource not found", status=404, success=False)

@api_bp.errorhandler(500)
def api_internal_error(error):
    return api_response(message="Internal server error", status=500, success=False)