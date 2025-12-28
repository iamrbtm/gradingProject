"""
Flask CLI commands for assignment synchronization.
Note: This file previously contained Reminders sync functionality which has been removed.
Only Google Tasks sync remains active in the main application.
"""

import click
from flask import current_app
from flask.cli import with_appcontext
from app.models import Assignment, Course, Term, db


@click.command()
@with_appcontext
def sync_status():
    """Show sync status for all assignments."""
    
    assignments = Assignment.query.join(Course).join(Term).filter(
        Term.active == True,
        Assignment.score.is_(None)
    ).order_by(Assignment.due_date).all()
    
    if not assignments:
        click.echo("No ungraded assignments found in active terms.")
        return
    
    click.echo(f"Assignment Status ({len(assignments)} assignments):")
    click.echo("-" * 50)
    
    for assignment in assignments:
        due_str = assignment.due_date.strftime("%Y-%m-%d") if assignment.due_date else "No due date"
        tasks_status = "✓" if assignment.last_synced_tasks else "✗"
        
        click.echo(f"{assignment.name[:40]:<40} | {assignment.course.name[:15]:<15} | {due_str} | Tasks:{tasks_status}")


def init_sync_commands(app):
    """Initialize sync commands with the Flask app."""
    app.cli.add_command(sync_status)