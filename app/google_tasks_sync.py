"""
Google Tasks Sync Manager
Replaces Apple Reminders sync with Google Tasks integration
"""
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from googleapiclient.errors import HttpError
from flask import current_app

from .google_auth import GoogleAuthManager
from .models import Assignment, Course, db

logger = logging.getLogger(__name__)

class GoogleTasksSyncManager:
    """Manages syncing assignments to Google Tasks"""
    
    def __init__(self):
        self.auth_manager = GoogleAuthManager()
        self.progress = {'current': 0, 'total': 0, 'status': 'ready', 'message': ''}
        self.task_list_id = None
        self.start_time = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with Google Tasks"""
        return self.auth_manager.get_credentials() is not None
    
    def get_auth_url(self) -> Optional[str]:
        """Get Google OAuth authorization URL"""
        return self.auth_manager.get_authorization_url()
    
    def handle_auth_callback(self, code: str, state: str) -> bool:
        """Handle OAuth callback"""
        return self.auth_manager.handle_auth_callback(code, state)
    
    def disconnect(self):
        """Disconnect from Google Tasks"""
        self.auth_manager.revoke_credentials()
    
    def get_or_create_task_list(self, list_name: str = "School Assignments") -> Optional[str]:
        """Get or create a task list for assignments"""
        try:
            service = self.auth_manager.get_tasks_service()
            if not service:
                return None
            
            # Get all task lists
            task_lists = service.tasklists().list().execute()
            
            # Look for existing list
            for task_list in task_lists.get('items', []):
                if task_list['title'] == list_name:
                    self.task_list_id = task_list['id']
                    return task_list['id']
            
            # Create new task list if it doesn't exist
            new_list = {
                'title': list_name
            }
            result = service.tasklists().insert(body=new_list).execute()
            self.task_list_id = result['id']
            return result['id']
            
        except HttpError as e:
            logger.error(f'Error getting/creating task list: {e}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error in get_or_create_task_list: {e}')
            return None
    
    def create_task_from_assignment(self, assignment: Assignment) -> Optional[str]:
        """Create a Google Task from an assignment"""
        try:
            service = self.auth_manager.get_tasks_service()
            if not service:
                return None
            
            if not self.task_list_id:
                self.task_list_id = self.get_or_create_task_list()
                if not self.task_list_id:
                    return None
            
            # Get course name safely
            course_name = "Unknown Course"
            try:
                course = Course.query.get(assignment.course_id)
                if course:
                    course_name = course.name
            except Exception as e:
                logger.warning(f'Could not get course name for assignment {assignment.id}: {e}')
            
            # Format task title and notes
            title = f"{course_name}: {assignment.name}"
            
            notes_parts = []
            if assignment.max_score and assignment.max_score > 0:
                notes_parts.append(f"Max Score: {assignment.max_score}")
            if assignment.category_id:
                try:
                    from .models import GradeCategory
                    category = GradeCategory.query.get(assignment.category_id)
                    if category:
                        notes_parts.append(f"Category: {category.name}")
                except Exception:
                    pass
            
            notes = "\n".join(notes_parts) if notes_parts else f"Assignment from {course_name}"
            
            # Create task body
            task_body = {
                'title': title,
                'notes': notes
            }
            
            # Add due date if available
            if assignment.due_date:
                # Convert to RFC 3339 format
                due_datetime = assignment.due_date
                if isinstance(due_datetime, str):
                    # Parse string date if needed
                    try:
                        due_datetime = datetime.fromisoformat(due_datetime.replace('Z', '+00:00'))
                    except Exception:
                        due_datetime = datetime.strptime(due_datetime, '%Y-%m-%d')
                
                # Format for Google Tasks (date only)
                task_body['due'] = due_datetime.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Create the task
            result = service.tasks().insert(
                tasklist=self.task_list_id,
                body=task_body
            ).execute()
            
            return result.get('id')
            
        except HttpError as e:
            logger.error(f'HTTP error creating task for assignment {assignment.id}: {e}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error creating task for assignment {assignment.id}: {e}')
            return None
    
    def update_task_from_assignment(self, task_id: str, assignment: Assignment) -> bool:
        """Update an existing Google Task from an assignment"""
        try:
            service = self.auth_manager.get_tasks_service()
            if not service or not self.task_list_id:
                return False
            
            # Get current task
            current_task = service.tasks().get(
                tasklist=self.task_list_id,
                task=task_id
            ).execute()
            
            # Get course name safely
            course_name = "Unknown Course"
            try:
                course = Course.query.get(assignment.course_id)
                if course:
                    course_name = course.name
            except Exception as e:
                logger.warning(f'Could not get course name for assignment {assignment.id}: {e}')
            
            # Update task fields
            current_task['title'] = f"{course_name}: {assignment.name}"
            
            notes_parts = []
            if assignment.max_score and assignment.max_score > 0:
                notes_parts.append(f"Max Score: {assignment.max_score}")
            if assignment.category_id:
                try:
                    from .models import GradeCategory
                    category = GradeCategory.query.get(assignment.category_id)
                    if category:
                        notes_parts.append(f"Category: {category.name}")
                except Exception:
                    pass
            
            current_task['notes'] = "\n".join(notes_parts) if notes_parts else f"Assignment from {course_name}"
            
            # Update due date
            if assignment.due_date:
                due_datetime = assignment.due_date
                if isinstance(due_datetime, str):
                    try:
                        due_datetime = datetime.fromisoformat(due_datetime.replace('Z', '+00:00'))
                    except Exception:
                        due_datetime = datetime.strptime(due_datetime, '%Y-%m-%d')
                
                current_task['due'] = due_datetime.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            else:
                current_task.pop('due', None)
            
            # Update the task
            service.tasks().update(
                tasklist=self.task_list_id,
                task=task_id,
                body=current_task
            ).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f'HTTP error updating task {task_id}: {e}')
            return False
        except Exception as e:
            logger.error(f'Unexpected error updating task {task_id}: {e}')
            return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a Google Task"""
        try:
            service = self.auth_manager.get_tasks_service()
            if not service or not self.task_list_id:
                return False
            
            service.tasks().delete(
                tasklist=self.task_list_id,
                task=task_id
            ).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f'HTTP error deleting task {task_id}: {e}')
            return False
        except Exception as e:
            logger.error(f'Unexpected error deleting task {task_id}: {e}')
            return False
    
    def sync_assignment(self, assignment: Assignment) -> Dict[str, Any]:
        """Sync a single assignment to Google Tasks"""
        result = {
            'success': False,
            'assignment_id': assignment.id,
            'assignment_name': assignment.name,
            'message': '',
            'task_id': None
        }
        
        try:
            if not self.is_authenticated():
                result['message'] = 'Not authenticated with Google Tasks'
                return result
            
            # Initialize task list
            if not self.task_list_id:
                if not self.get_or_create_task_list():
                    result['message'] = 'Failed to get or create task list'
                    return result
            
            # Check for existing task (duplicate prevention)
            if assignment.google_task_id:
                # Try to update existing task
                if self.update_task_from_assignment(assignment.google_task_id, assignment):
                    # Update database timestamp
                    assignment.last_synced_tasks = datetime.utcnow()
                    db.session.commit()
                    
                    result['success'] = True
                    result['task_id'] = assignment.google_task_id
                    result['message'] = 'Successfully updated existing task in Google Tasks'
                else:
                    # If update failed, task might have been deleted, create new one
                    assignment.google_task_id = None
                    
            # Create new task if none exists
            if not assignment.google_task_id:
                task_id = self.create_task_from_assignment(assignment)
                if task_id:
                    # Update database with task ID and timestamp
                    assignment.google_task_id = task_id
                    assignment.last_synced_tasks = datetime.utcnow()
                    db.session.commit()
                    
                    result['success'] = True
                    result['task_id'] = task_id
                    result['message'] = 'Successfully created new task in Google Tasks'
                else:
                    result['message'] = 'Failed to create task in Google Tasks'
            
        except Exception as e:
            logger.error(f'Error syncing assignment {assignment.id}: {e}')
            result['message'] = f'Error: {str(e)}'
            # Rollback any database changes on error
            try:
                db.session.rollback()
            except Exception:
                pass
        
        return result
    
    def sync_assignments(self, assignments: List[Assignment]) -> Dict[str, Any]:
        """Sync multiple assignments to Google Tasks"""
        if not assignments:
            return {
                'success': True,
                'total': 0,
                'synced': 0,
                'failed': 0,
                'results': [],
                'message': 'No assignments to sync'
            }
        
        # Initialize progress and start timer
        self.start_time = time.time()
        self.progress = {
            'current': 0,
            'total': len(assignments),
            'status': 'syncing',
            'message': 'Starting sync...'
        }
        
        results = []
        synced_count = 0
        failed_count = 0
        
        # Initialize task list
        if not self.get_or_create_task_list():
            return {
                'success': False,
                'total': len(assignments),
                'synced': 0,
                'failed': len(assignments),
                'results': [],
                'message': 'Failed to initialize Google Tasks'
            }
        
        for i, assignment in enumerate(assignments):
            self.progress['current'] = i + 1
            self.progress['message'] = f'Syncing: {assignment.name}'
            
            result = self.sync_assignment(assignment)
            results.append(result)
            
            if result['success']:
                synced_count += 1
            else:
                failed_count += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        self.progress['status'] = 'completed'
        self.progress['message'] = f'Sync completed: {synced_count} succeeded, {failed_count} failed'
        
        return {
            'success': failed_count == 0,
            'total': len(assignments),
            'synced': synced_count,
            'failed': failed_count,
            'results': results,
            'message': f'Synced {synced_count} of {len(assignments)} assignments'
        }
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current sync progress"""
        return self.progress.copy()
    
    def clear_all_synced_assignments(self, assignments: List[Assignment]) -> Dict[str, Any]:
        """Clear all synced assignments from Google Tasks and database"""
        if not assignments:
            return {
                'success': True,
                'total': 0,
                'cleared': 0,
                'failed': 0,
                'message': 'No assignments to clear'
            }
        
        # Filter to only assignments that have Google Task IDs
        synced_assignments = [a for a in assignments if a.google_task_id]
        
        if not synced_assignments:
            return {
                'success': True,
                'total': len(assignments),
                'cleared': 0,
                'failed': 0,
                'message': 'No synced assignments to clear'
            }
        
        # Initialize progress and start timer
        self.start_time = time.time()
        self.progress = {
            'current': 0,
            'total': len(synced_assignments),
            'status': 'clearing',
            'message': 'Starting clear operation...'
        }
        
        cleared_count = 0
        failed_count = 0
        results = []
        
        # Initialize task list
        if not self.get_or_create_task_list():
            return {
                'success': False,
                'total': len(synced_assignments),
                'cleared': 0,
                'failed': len(synced_assignments),
                'message': 'Failed to initialize Google Tasks'
            }
        
        for i, assignment in enumerate(synced_assignments):
            self.progress['current'] = i + 1
            self.progress['message'] = f'Clearing: {assignment.name}'
            
            result = {
                'assignment_id': assignment.id,
                'assignment_name': assignment.name,
                'success': False,
                'message': ''
            }
            
            try:
                # Delete from Google Tasks
                if self.delete_task(assignment.google_task_id):
                    # Clear database fields
                    assignment.google_task_id = None
                    assignment.last_synced_tasks = None
                    db.session.commit()
                    
                    result['success'] = True
                    result['message'] = 'Successfully cleared from Google Tasks'
                    cleared_count += 1
                else:
                    # Even if deletion failed, clear database (task might not exist)
                    assignment.google_task_id = None
                    assignment.last_synced_tasks = None
                    db.session.commit()
                    
                    result['success'] = True
                    result['message'] = 'Cleared from database (task may not have existed in Google Tasks)'
                    cleared_count += 1
                    
            except Exception as e:
                logger.error(f'Error clearing assignment {assignment.id}: {e}')
                result['message'] = f'Error: {str(e)}'
                failed_count += 1
                # Rollback database changes on error
                try:
                    db.session.rollback()
                except Exception:
                    pass
            
            results.append(result)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        self.progress['status'] = 'completed'
        self.progress['message'] = f'Clear completed: {cleared_count} cleared, {failed_count} failed'
        
        return {
            'success': failed_count == 0,
            'total': len(synced_assignments),
            'cleared': cleared_count,
            'failed': failed_count,
            'results': results,
            'message': f'Cleared {cleared_count} of {len(synced_assignments)} synced assignments'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Google Tasks connection"""
        try:
            if not self.is_authenticated():
                return {
                    'success': False,
                    'message': 'Not authenticated with Google Tasks'
                }
            
            service = self.auth_manager.get_tasks_service()
            if not service:
                return {
                    'success': False,
                    'message': 'Failed to create Google Tasks service'
                }
            
            # Try to list task lists
            task_lists = service.tasklists().list().execute()
            list_count = len(task_lists.get('items', []))
            
            return {
                'success': True,
                'message': f'Connected to Google Tasks. Found {list_count} task lists.'
            }
            
        except HttpError as e:
            return {
                'success': False,
                'message': f'Google Tasks API error: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test failed: {e}'
            }