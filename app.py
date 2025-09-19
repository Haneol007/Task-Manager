#!/usr/bin/env python3
"""
TaskFlow Pro - Professional Task Management System

This is the main application entry point for TaskFlow Pro, a comprehensive
task management web application built with Flask.

Features:
- User authentication and authorization
- Task creation, editing, and deletion
- Project organization
- Priority and status management
- Due date tracking
- Analytics and reporting
- RESTful API
- Responsive web interface

INTENTIONAL BUG NOTICE:
This application contains an intentional bug in the task deletion functionality
(see app/views/tasks.py:delete_task) that demonstrates cascading deletion issues
in database relationships. This bug causes orphaned records and data inconsistency.

Author: TaskFlow Pro Development Team
Version: 1.0.0
"""

import os
from app import create_app, db
from app.models.user import User
from app.models.task import Task, TaskComment, TaskAttachment
from app.models.project import Project

# Create the Flask application
app = create_app()

# CLI commands for database management
@app.cli.command()
def init_db():
    """Initialize the database with tables."""
    db.create_all()
    print("Database initialized successfully!")

@app.cli.command()
def seed_db():
    """Seed the database with sample data."""
    # Create a demo user
    demo_user = User(
        username='demo_user',
        email='demo@taskflowpro.com',
        password='DemoPassword123',
        first_name='Demo',
        last_name='User'
    )
    db.session.add(demo_user)
    db.session.flush()  # Get the user ID
    
    # Create sample projects
    project1 = Project(
        name='Website Redesign',
        description='Complete redesign of company website',
        user_id=demo_user.id,
        color='#007bff'
    )
    
    project2 = Project(
        name='Marketing Campaign',
        description='Q4 marketing campaign launch',
        user_id=demo_user.id,
        color='#28a745'
    )
    
    db.session.add_all([project1, project2])
    db.session.flush()
    
    # Create sample tasks
    from app.models.task import TaskPriority, TaskStatus
    from datetime import datetime, timedelta
    
    tasks = [
        Task(
            title='Design new homepage layout',
            description='Create mockups and wireframes for the new homepage design',
            user_id=demo_user.id,
            project_id=project1.id,
            priority=TaskPriority.HIGH,
            due_date=datetime.utcnow() + timedelta(days=7)
        ),
        Task(
            title='Set up development environment',
            description='Configure local development setup with necessary tools',
            user_id=demo_user.id,
            project_id=project1.id,
            priority=TaskPriority.MEDIUM,
            is_completed=True,
            completed_at=datetime.utcnow() - timedelta(days=2)
        ),
        Task(
            title='Research competitor websites',
            description='Analyze competitor websites for design inspiration',
            user_id=demo_user.id,
            project_id=project1.id,
            priority=TaskPriority.LOW,
            due_date=datetime.utcnow() + timedelta(days=14)
        ),
        Task(
            title='Create social media content calendar',
            description='Plan and schedule social media posts for the campaign',
            user_id=demo_user.id,
            project_id=project2.id,
            priority=TaskPriority.HIGH,
            due_date=datetime.utcnow() + timedelta(days=3)
        ),
        Task(
            title='Design banner advertisements',
            description='Create banner ads for various platforms',
            user_id=demo_user.id,
            project_id=project2.id,
            priority=TaskPriority.MEDIUM,
            due_date=datetime.utcnow() + timedelta(days=10)
        ),
        # Add an overdue task to demonstrate the bug
        Task(
            title='Update customer database',
            description='Clean and update customer contact information',
            user_id=demo_user.id,
            priority=TaskPriority.URGENT,
            due_date=datetime.utcnow() - timedelta(days=3)  # Overdue
        ),
        # Add a task with subtasks to demonstrate the cascading deletion bug
        Task(
            title='Launch product beta',
            description='Coordinate the beta launch of our new product',
            user_id=demo_user.id,
            priority=TaskPriority.HIGH,
            due_date=datetime.utcnow() + timedelta(days=21)
        )
    ]
    
    db.session.add_all(tasks)
    db.session.flush()
    
    # Add subtasks to demonstrate the bug
    parent_task = tasks[-1]  # "Launch product beta"
    subtasks = [
        Task(
            title='Send beta invitations',
            description='Send invitation emails to beta testers',
            user_id=demo_user.id,
            parent_task_id=parent_task.id,
            priority=TaskPriority.HIGH,
            due_date=datetime.utcnow() + timedelta(days=7)
        ),
        Task(
            title='Set up beta feedback system',
            description='Configure system to collect beta user feedback',
            user_id=demo_user.id,
            parent_task_id=parent_task.id,
            priority=TaskPriority.MEDIUM,
            due_date=datetime.utcnow() + timedelta(days=14)
        )
    ]
    
    db.session.add_all(subtasks)
    db.session.commit()
    
    print(f"Database seeded successfully!")
    print(f"Demo user created: {demo_user.username} (password: DemoPassword123)")
    print(f"Created {len(tasks)} main tasks and {len(subtasks)} subtasks")
    print(f"Created {len([project1, project2])} projects")

@app.cli.command()
def create_admin():
    """Create an admin user."""
    username = input("Enter admin username: ")
    email = input("Enter admin email: ")
    password = input("Enter admin password: ")
    first_name = input("Enter first name: ")
    last_name = input("Enter last name: ")
    
    admin_user = User(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )
    admin_user.is_admin = True
    
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"Admin user '{username}' created successfully!")

# Shell context for easier debugging
@app.shell_context_processor
def make_shell_context():
    """Make database models available in flask shell."""
    return {
        'db': db,
        'User': User,
        'Task': Task,
        'TaskComment': TaskComment,
        'TaskAttachment': TaskAttachment,
        'Project': Project
    }

if __name__ == '__main__':
    # Development server configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("TaskFlow Pro - Professional Task Management System")
    print("=" * 60)
    print(f"Starting development server on port {port}")
    print(f"Debug mode: {debug}")
    print("")
    print("IMPORTANT NOTICE:")
    print("This application contains an INTENTIONAL BUG in task deletion")
    print("functionality to demonstrate database cascading issues.")
    print("See app/views/tasks.py:delete_task for details.")
    print("")
    print("To get started:")
    print("1. Visit http://localhost:5000")
    print("2. Register a new account or use demo data:")
    print("   flask seed-db")
    print("3. Try deleting tasks with subtasks to trigger the bug!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)