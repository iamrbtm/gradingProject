"""
Canvas Sync Service

This service handles syncing Canvas data with the local database models.
Maps Canvas courses, assignments, and grades to local Course, Assignment models.
"""

import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

logger = logging.getLogger(__name__)

# Import canvas sync logging utilities
try:
    from app.logging_config import (
        log_canvas_sync_event,
        log_canvas_api_call,
        log_canvas_db_operation,
        log_canvas_progress,
        log_canvas_error,
    )
except ImportError:
    # Fallback if logging config not available
    def log_canvas_sync_event(*args, **kwargs):
        pass

    def log_canvas_api_call(*args, **kwargs):
        pass

    def log_canvas_db_operation(*args, **kwargs):
        pass

    def log_canvas_progress(*args, **kwargs):
        pass

    def log_canvas_error(*args, **kwargs):
        pass


db = None
Term = None
Course = None
Assignment = None
GradeCategory = None


def _ensure_models():
    global db, Term, Course, Assignment, GradeCategory
    missing_db = db is None
    missing_Term = Term is None
    missing_Course = Course is None
    missing_Assignment = Assignment is None
    missing_GradeCategory = GradeCategory is None

    if not (
        missing_db
        or missing_Term
        or missing_Course
        or missing_Assignment
        or missing_GradeCategory
    ):
        return

    try:
        from ..models import (
            db as _db,
            Term as _Term,
            Course as _Course,
            Assignment as _Assignment,
            GradeCategory as _GradeCategory,
        )
    except Exception:
        return

    if missing_db:
        db = _db
    if missing_Term:
        Term = _Term
    if missing_Course:
        Course = _Course
    if missing_Assignment:
        Assignment = _Assignment
    if missing_GradeCategory:
        GradeCategory = _GradeCategory


class CanvasSyncError(Exception):
    """Custom exception for Canvas sync errors"""

    pass


class CanvasSyncService:
    """
    Service for syncing Canvas data with local database models

    Handles:
    - Fetching data from Canvas API
    - Mapping Canvas data to local models
    - Creating/updating local records
    - Tracking sync status and timestamps
    """

    def __init__(
        self,
        user,
        canvas_api_service,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize Canvas sync service for a specific user

        Args:
            user: User instance with Canvas credentials
            canvas_api_service: CanvasAPIService instance
            progress_callback: Optional callback function for progress updates
        """
        self.user = user
        self.canvas_api = canvas_api_service
        self.progress_callback = progress_callback
        self.start_time = None

    def _update_progress(
        self, current: int, total: int, operation: str = "", item_name: str = ""
    ):
        """
        Update progress if callback is provided

        Args:
            current: Current item count
            total: Total items to process
            operation: Current operation description
            item_name: Name of current item being processed
        """
        if self.progress_callback:
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            progress_data = {
                "progress_percent": int((current / total) * 100) if total > 0 else 0,
                "completed_items": current,
                "total_items": total,
                "current_operation": operation,
                "current_item": item_name,
                "elapsed_time": round(elapsed_time, 1),
                "errors": [],
            }
            self.progress_callback(progress_data)

    def test_connection(self) -> Dict[str, Any]:
        """
        Test Canvas API connection

        Returns:
            Dict with sync results and statistics
        """
        _ensure_models()

        logger.info(f"Testing Canvas API connection for user {self.user.id}")

        if not self.canvas_api:
            error_msg = "Canvas API not initialized"
            logger.error(error_msg)
            log_canvas_error(
                error_msg, user_id=self.user.id, operation="test_connection"
            )
            return {
                "success": False,
                "error": error_msg,
                "message": "Canvas credentials not configured",
            }

        result = self.canvas_api.test_connection()

        if result.get("success"):
            logger.info(f"Canvas API connection successful: {result.get('message')}")
            log_canvas_api_call(
                "GET",
                "/users/self",
                user_id=self.user.id,
                response_status=200,
            )
        else:
            logger.error(f"Canvas API connection failed: {result.get('error')}")
            log_canvas_error(
                result.get("error", "Unknown error"),
                user_id=self.user.id,
                operation="test_connection",
            )

        return result

    def _parse_canvas_term(
        self, canvas_term: Optional[Dict[str, Any]]
    ) -> Tuple[str, int]:
        """
        Parse Canvas term data to extract season and year

        Args:
            canvas_term: Canvas term object from API

        Returns:
            Tuple of (season, year) e.g. ("Spring", 2025)
        """
        if not canvas_term or not canvas_term.get("name"):
            # Default to current year and Fall season if no term data
            current_year = datetime.now().year
            return ("Fall", current_year)

        term_name = canvas_term["name"].strip()

        # Extract year - look for 4-digit year
        year_match = re.search(r"20\d{2}", term_name)
        year = int(year_match.group()) if year_match else datetime.now().year

        # Extract season - look for common patterns
        term_lower = term_name.lower()
        if any(s in term_lower for s in ["spring", "spr"]):
            season = "Spring"
        elif any(s in term_lower for s in ["summer", "sum"]):
            season = "Summer"
        elif any(s in term_lower for s in ["fall", "autumn", "fal"]):
            season = "Fall"
        elif any(s in term_lower for s in ["winter", "win"]):
            season = "Winter"
        else:
            # Default to Fall if we can't determine season
            season = "Fall"

        logger.info(f"Parsed Canvas term '{term_name}' as {season} {year}")
        return (season, year)

    def _find_or_create_term(
        self, season: str, year: int, flush: bool = True
    ) -> Union[int, Any]:
        """
        Find existing term or create new one

        Args:
            season: Season name (Spring, Summer, Fall, Winter)
            year: Year (e.g. 2025)
            flush: Whether to flush immediately (default: True for backwards compatibility)

        Returns:
            Term ID (int) if flushed, Term object if not flushed
        """
        _ensure_models()

        # Look for existing term
        existing_term = Term.query.filter_by(
            user_id=self.user.id, season=season, year=year
        ).first()

        if existing_term:
            logger.info(
                f"Found existing term: {season} {year} (ID: {existing_term.id})"
            )
            return existing_term.id

        # Create new term
        new_term = Term(
            user_id=self.user.id,
            season=season,
            year=year,
            nickname=f"{season} {year}",  # Auto-generate nickname
            school_name="Canvas Import",  # Default school name for Canvas imports
            active=True,  # Make new terms active by default
        )

        # Deactivate other terms when creating a new one
        Term.query.filter_by(user_id=self.user.id, active=True).update(
            {"active": False}
        )

        db.session.add(new_term)

        if flush:
            db.session.flush()
            logger.info(f"Created new term: {season} {year} (ID: {new_term.id})")
            return new_term.id
        else:
            logger.info(f"Created new term: {season} {year} (will flush later)")
            return new_term

    def sync_term_data(
        self, term_id: int, force_full_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Sync Canvas data for a specific term only

        Args:
            term_id: Term ID to sync data for
            force_full_sync: If True, clear existing assignments and categories before syncing

        Returns:
            Dict with sync results and statistics
        """
        _ensure_models()

        if not self.canvas_api:
            raise CanvasSyncError("Canvas API not initialized")

        try:
            # Initialize progress tracking
            self.start_time = time.time()

            # Get the term to sync
            term = Term.query.filter_by(id=term_id, user_id=self.user.id).first()
            if not term:
                raise CanvasSyncError(f"Term {term_id} not found")

            # Fetch Canvas courses
            logger.info(f"Starting Canvas sync for term {term_id} ({term.nickname})")
            self._update_progress(0, 100, f"Fetching courses for term: {term.nickname}")

            canvas_courses = self.canvas_api.get_courses()
            total_courses = len(canvas_courses)
            self._update_progress(
                0,
                total_courses,
                f"Syncing {total_courses} courses to term: {term.nickname}",
            )

            sync_results = {
                "courses_processed": 0,
                "courses_created": 0,
                "courses_updated": 0,
                "assignments_processed": 0,
                "assignments_created": 0,
                "assignments_updated": 0,
                "categories_created": 0,
                "errors": [],
            }

            # If force_full_sync, clear existing assignments and categories for courses in this term
            if force_full_sync:
                logger.info(
                    "Force full sync enabled - clearing existing assignments and categories"
                )
                _ensure_models()

                courses_in_term = Course.query.filter_by(term_id=term_id).all()
                for course in courses_in_term:
                    # Delete assignments
                    Assignment.query.filter_by(course_id=course.id).delete()
                    # Delete categories
                    GradeCategory.query.filter_by(course_id=course.id).delete()
                db.session.commit()
                logger.info(f"Cleared existing data for {len(courses_in_term)} courses")

            # Sync all courses to this term (no filtering by Canvas term data)
            for idx, canvas_course in enumerate(canvas_courses, 1):
                try:
                    course_name = canvas_course.get("name", "Unnamed Course")
                    self._update_progress(
                        idx - 1,
                        total_courses,
                        f"Syncing course: {course_name}",
                        course_name,
                    )

                    course_result = self._sync_course(canvas_course, term_id)

                    sync_results["courses_processed"] += 1
                    if course_result["created"]:
                        sync_results["courses_created"] += 1
                    else:
                        sync_results["courses_updated"] += 1

                    sync_results["assignments_processed"] += course_result[
                        "assignments_processed"
                    ]
                    sync_results["assignments_created"] += course_result[
                        "assignments_created"
                    ]
                    sync_results["assignments_updated"] += course_result[
                        "assignments_updated"
                    ]
                    sync_results["categories_created"] += course_result[
                        "categories_created"
                    ]

                except Exception as e:
                    error_msg = f"Failed to sync course {canvas_course.get('name', 'Unknown')}: {e}"
                    logger.error(error_msg)
                    sync_results["errors"].append(error_msg)

            # Update user's last sync timestamp
            self.user.canvas_last_sync = datetime.utcnow()
            db.session.commit()

            # Final progress update
            self._update_progress(
                total_courses, total_courses, f"Term sync completed successfully!"
            )

            logger.info(
                f"Canvas term sync completed for term {term_id}: {sync_results}"
            )
            return sync_results

        except Exception as e:
            db.session.rollback()
            logger.error(f"Canvas term sync failed for term {term_id}: {e}")
            raise CanvasSyncError(f"Term sync failed: {e}")

    def sync_course_data(self, course_id: int) -> Dict[str, Any]:
        """
        Sync Canvas data for a specific course only

        Args:
            course_id: Course ID to sync data for

        Returns:
            Dict with sync results and statistics
        """
        _ensure_models()

        if not self.canvas_api:
            raise CanvasSyncError("Canvas API not initialized")

        try:
            # Initialize progress tracking
            self.start_time = time.time()

            from concurrent.futures import ThreadPoolExecutor

            # Get the course to sync (ensure it belongs to current user)
            course = (
                Course.query.join(Term)
                .filter(Course.id == course_id, Term.user_id == self.user.id)
                .first()
            )
            if not course:
                raise CanvasSyncError(f"Course {course_id} not found or access denied")

            if not course.canvas_course_id:
                raise CanvasSyncError(f"Course {course.name} is not linked to Canvas")

            logger.info(f"Starting Canvas sync for course: {course.name}")
            logger.info("-" * 60)

            self._update_progress(0, 100, f"Starting sync for course: {course.name}")

            # Fetch Canvas course data
            canvas_course_id = course.canvas_course_id

            # Fetch all Canvas data concurrently
            logger.info("Fetching assignments, groups, and submissions...")
            self._update_progress(
                10, 100, "Fetching assignments, groups, and submissions..."
            )

            with ThreadPoolExecutor(max_workers=3) as executor:
                future_assignments = executor.submit(
                    self.canvas_api.get_assignments, canvas_course_id
                )
                future_groups = executor.submit(
                    self.canvas_api.get_assignment_groups, canvas_course_id
                )
                future_submissions = executor.submit(
                    self.canvas_api.get_submissions, canvas_course_id
                )

                # Wait for all requests to complete
                canvas_assignments = future_assignments.result()
                canvas_groups = future_groups.result()
                all_submissions = future_submissions.result()

            logger.info(
                f"Found {len(canvas_assignments)} assignments, {len(canvas_groups)} groups, "
                f"{len(all_submissions)} submissions"
            )

            # Create assignment groups (categories) mapping
            logger.info("Creating assignment categories...")
            self._update_progress(20, 100, "Creating assignment categories...")
            group_mapping = self._create_assignment_groups(canvas_groups, course.id)

            # Create submissions lookup by assignment ID for O(1) access
            submissions_by_assignment = {}
            for submission in all_submissions:
                assignment_id = str(submission.get("assignment_id", ""))
                if assignment_id:
                    submissions_by_assignment[assignment_id] = submission

            results = {
                "assignments_processed": 0,
                "assignments_created": 0,
                "assignments_updated": 0,
                "categories_created": len(group_mapping),
            }

            # Process each assignment with pre-fetched submission data (no flush per assignment)
            logger.info(f"Syncing {len(canvas_assignments)} assignments...")
            total_assignments = len(canvas_assignments)

            for idx, canvas_assignment in enumerate(canvas_assignments, 1):
                try:
                    canvas_assignment_id = str(canvas_assignment["id"])
                    assignment_name = canvas_assignment.get(
                        "name", "Unnamed Assignment"
                    )
                    submission = submissions_by_assignment.get(canvas_assignment_id)

                    # Update progress (20-90% range for assignment processing)
                    progress_percent = 20 + int((idx / total_assignments) * 70)
                    self._update_progress(
                        progress_percent,
                        100,
                        f"Processing assignment: {assignment_name}",
                        assignment_name,
                    )

                    assignment_result = self._sync_assignment(
                        canvas_assignment,
                        canvas_course_id,
                        course.id,
                        group_mapping,
                        submission,  # Pass pre-fetched submission
                        flush=False,  # Don't flush per assignment, batch them
                    )

                    results["assignments_processed"] += 1
                    if assignment_result["created"]:
                        results["assignments_created"] += 1
                    else:
                        results["assignments_updated"] += 1

                    if idx % 10 == 0 or idx == len(canvas_assignments):
                        logger.info(
                            f"  Progress: {idx}/{len(canvas_assignments)} assignments processed"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to sync assignment {canvas_assignment.get('name', 'Unknown')}: {e}"
                    )

            # Single flush for all assignments
            if results["assignments_processed"] > 0:
                _ensure_models()
                db.session.flush()
                logger.info(
                    f"Flushed {results['assignments_processed']} assignments in batch"
                )

            # Update course last sync timestamp
            course.last_synced_canvas = datetime.utcnow()
            db.session.commit()

            # Final progress update
            self._update_progress(100, 100, f"Course sync completed successfully!")

            logger.info("-" * 60)
            logger.info(
                f"Course sync completed: {results['assignments_created']} created, "
                f"{results['assignments_updated']} updated, "
                f"{results['categories_created']} categories"
            )
            return results

        except Exception as e:
            db.session.rollback()
            logger.error(f"Canvas course sync failed for course {course_id}: {e}")
            raise CanvasSyncError(f"Course sync failed: {e}")

    def sync_all_data(
        self, term_id: Optional[int] = None, use_incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Sync all Canvas data for the user

        Args:
            term_id: Optional term ID to sync to. If not provided, will auto-create terms from Canvas data.
            use_incremental: If True, only sync courses updated since last sync (default: False)

        Returns:
            Dict with sync results and statistics
        """
        _ensure_models()

        if not self.canvas_api:
            error_msg = "Canvas API not initialized"
            logger.error(error_msg)
            log_canvas_error(error_msg, user_id=self.user.id, operation="sync_all_data")
            raise CanvasSyncError(error_msg)

        try:
            # Initialize progress tracking
            self.start_time = time.time()

            # Fetch Canvas data
            logger.info(f"Starting Canvas sync for user {self.user.id}")
            logger.info("=" * 60)

            # Use incremental sync if requested and we have a last sync timestamp
            since = None
            if use_incremental and self.user.canvas_last_sync:
                since = self.user.canvas_last_sync
                logger.info(f"Using incremental sync since {since}")
                log_canvas_sync_event(
                    "incremental_sync_enabled",
                    user_id=self.user.id,
                    since=since.isoformat(),
                )

            self._update_progress(0, 100, "Fetching courses from Canvas...")

            logger.info("Fetching courses from Canvas...")
            canvas_courses = self.canvas_api.get_courses(since=since)
            logger.info(f"Found {len(canvas_courses)} courses to sync")
            log_canvas_api_call(
                "GET",
                "/courses",
                user_id=self.user.id,
                response_status=200,
                count=len(canvas_courses),
            )

            total_courses = len(canvas_courses)
            self._update_progress(
                0, total_courses, f"Syncing {total_courses} courses..."
            )

            sync_results = {
                "courses_processed": 0,
                "courses_created": 0,
                "courses_updated": 0,
                "assignments_processed": 0,
                "assignments_created": 0,
                "assignments_updated": 0,
                "categories_created": 0,
                "errors": [],
            }

            # Process each Canvas course
            for idx, canvas_course in enumerate(canvas_courses, 1):
                try:
                    course_name = canvas_course.get("name", "Unnamed Course")
                    canvas_course_id = str(canvas_course.get("id", ""))
                    logger.info(
                        f"[{idx}/{len(canvas_courses)}] Syncing course: {course_name}"
                    )

                    # Update progress
                    self._update_progress(
                        idx - 1,
                        total_courses,
                        f"Syncing course: {course_name}",
                        course_name,
                    )

                    # Determine which term this course belongs to
                    if term_id:
                        # Use provided term_id for all courses
                        course_term_id = term_id
                        logger.debug(
                            f"Using provided term {term_id} for course {course_name}"
                        )
                    else:
                        # Auto-determine term from Canvas data
                        canvas_term = canvas_course.get("term")
                        season, year = self._parse_canvas_term(canvas_term)
                        course_term_id = self._find_or_create_term(season, year)
                        logger.debug(
                            f"Auto-determined term {season} {year} for course {course_name}"
                        )

                    course_result = self._sync_course(canvas_course, course_term_id)

                    # Update results
                    sync_results["courses_processed"] += 1
                    if course_result["created"]:
                        sync_results["courses_created"] += 1
                        logger.info(f"✓ Created course: {course_name}")
                    else:
                        sync_results["courses_updated"] += 1
                        logger.info(f"✓ Updated course: {course_name}")

                    sync_results["assignments_processed"] += course_result[
                        "assignments_processed"
                    ]
                    sync_results["assignments_created"] += course_result[
                        "assignments_created"
                    ]
                    sync_results["assignments_updated"] += course_result[
                        "assignments_updated"
                    ]
                    sync_results["categories_created"] += course_result[
                        "categories_created"
                    ]

                    log_canvas_db_operation(
                        "sync",
                        "Course",
                        count=1,
                        course_id=canvas_course_id,
                        created=course_result["created"],
                        assignments_synced=course_result["assignments_processed"],
                    )

                except Exception as e:
                    error_msg = f"Failed to sync course {canvas_course.get('name', 'Unknown')}: {e}"
                    logger.error(f"  ✗ {error_msg}")
                    sync_results["errors"].append(error_msg)
                    log_canvas_error(
                        error_msg,
                        user_id=self.user.id,
                        course_id=canvas_course.get("id"),
                        operation="sync_course",
                    )

            # Update user's last sync timestamp
            self.user.canvas_last_sync = datetime.utcnow()
            db.session.commit()
            logger.info(f"Updated last sync timestamp for user {self.user.id}")

            # Final progress update
            self._update_progress(
                total_courses, total_courses, "Canvas sync completed successfully!"
            )

            logger.info("=" * 60)
            logger.info(f"Canvas sync completed for user {self.user.id}")
            logger.info(
                f"Summary: {sync_results['courses_processed']} courses, "
                f"{sync_results['assignments_processed']} assignments, "
                f"{sync_results['categories_created']} categories"
            )
            if sync_results["errors"]:
                logger.warning(
                    f"Encountered {len(sync_results['errors'])} errors during sync"
                )

            log_canvas_sync_event(
                "sync_all_completed",
                user_id=self.user.id,
                result=sync_results,
            )

            return sync_results

        except Exception as e:
            db.session.rollback()
            error_msg = f"Canvas sync failed for user {self.user.id}: {e}"
            logger.error(error_msg)
            log_canvas_error(str(e), user_id=self.user.id, operation="sync_all_data")
            raise CanvasSyncError(f"Sync failed: {e}")

    def _sync_course(
        self, canvas_course: Dict[str, Any], term_id: int, flush: bool = True
    ) -> Dict[str, Any]:
        """
        Sync a single Canvas course

        Args:
            canvas_course: Canvas course data
            term_id: Local term ID to associate with
            flush: Whether to flush after creating course (default: True)

        Returns:
            Dict with sync results for this course
        """
        _ensure_models()

        canvas_course_id = str(canvas_course["id"])
        course_name = canvas_course.get("name", "Unnamed Course")

        # Find or create local course
        local_course = Course.query.filter_by(
            canvas_course_id=canvas_course_id, term_id=term_id
        ).first()

        course_created = False
        if not local_course:
            # Create new course
            local_course = Course(
                name=course_name,
                credits=3.0,  # Default credits, user can adjust
                term_id=term_id,
                canvas_course_id=canvas_course_id,
                is_weighted=True,
                is_category=False,
            )
            db.session.add(local_course)
            course_created = True
            logger.info(f"Created new course: {course_name}")
        else:
            # Update existing course name if different
            if local_course.name != course_name:
                local_course.name = course_name
                logger.info(f"Updated course name: {course_name}")

        local_course.last_synced_canvas = datetime.utcnow()

        # Only flush if requested (for batch operations)
        if flush:
            db.session.flush()

        # Fetch and sync assignments
        assignment_results = self._sync_course_assignments(
            canvas_course_id, local_course.id
        )

        return {
            "created": course_created,
            "assignments_processed": assignment_results["assignments_processed"],
            "assignments_created": assignment_results["assignments_created"],
            "assignments_updated": assignment_results["assignments_updated"],
            "categories_created": assignment_results["categories_created"],
        }

    def _sync_course_assignments(
        self, canvas_course_id: str, local_course_id: int
    ) -> Dict[str, Any]:
        """
        Sync assignments for a specific course

        Args:
            canvas_course_id: Canvas course ID
            local_course_id: Local course ID

        Returns:
            Dict with assignment sync results
        """
        try:
            from .canvas_api_service import CanvasAPIError
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # Fetch all Canvas data concurrently
            logger.info(f"  Fetching data for course {canvas_course_id}...")
            canvas_assignments = []
            canvas_groups = []
            all_submissions = []

            try:
                with ThreadPoolExecutor(max_workers=3) as executor:
                    future_assignments = executor.submit(
                        self.canvas_api.get_assignments, canvas_course_id
                    )
                    future_groups = executor.submit(
                        self.canvas_api.get_assignment_groups, canvas_course_id
                    )
                    future_submissions = executor.submit(
                        self.canvas_api.get_submissions, canvas_course_id
                    )

                    # Wait for all requests to complete
                    canvas_assignments = future_assignments.result()
                    canvas_groups = future_groups.result()
                    all_submissions = future_submissions.result()
            except Exception as api_error:
                logger.error(
                    f"  API calls failed for course {canvas_course_id}: {api_error}"
                )
                # Try individual calls to see which one fails
                try:
                    canvas_assignments = self.canvas_api.get_assignments(
                        canvas_course_id
                    )
                    logger.info(
                        f"  Assignments API succeeded: {len(canvas_assignments)} assignments"
                    )
                except Exception as e:
                    logger.error(f"  Assignments API failed: {e}")
                    canvas_assignments = []  # Ensure initialized

                try:
                    canvas_groups = self.canvas_api.get_assignment_groups(
                        canvas_course_id
                    )
                    logger.info(f"  Groups API succeeded: {len(canvas_groups)} groups")
                except Exception as e:
                    logger.error(f"  Groups API failed: {e}")
                    canvas_groups = []  # Ensure initialized

                try:
                    all_submissions = self.canvas_api.get_submissions(canvas_course_id)
                    logger.info(
                        f"  Submissions API succeeded: {len(all_submissions)} submissions"
                    )
                except Exception as e:
                    logger.error(f"  Submissions API failed: {e}")
                    logger.warning(
                        "  Attempting fallback: fetching individual assignment submissions"
                    )

                    # Fallback: Try to get submissions for individual assignments
                    all_submissions = []
                    try:
                        for assignment in canvas_assignments:
                            assignment_id = str(assignment.get("id", ""))
                            if assignment_id:
                                try:
                                    submissions = self.canvas_api.get_submissions(
                                        canvas_course_id, assignment_id
                                    )
                                    all_submissions.extend(submissions)
                                    # Add small delay to avoid overwhelming the API
                                    import time

                                    time.sleep(0.1)
                                except Exception as sub_e:
                                    logger.warning(
                                        f"  Failed to get submission for assignment {assignment_id}: {sub_e}"
                                    )
                                    continue

                        logger.info(
                            f"  Fallback succeeded: {len(all_submissions)} submissions retrieved"
                        )
                    except Exception as fallback_e:
                        logger.error(f"  Fallback method also failed: {fallback_e}")
                        all_submissions = []

                    logger.warning("  Continuing sync without submission data")

            logger.info(
                f"  Final counts - assignments: {len(canvas_assignments)}, groups: {len(canvas_groups)}, submissions: {len(all_submissions)}"
            )

            # Create assignment groups (categories) mapping
            group_mapping = self._create_assignment_groups(
                canvas_groups, local_course_id
            )

            # Create submissions lookup by assignment ID for O(1) access
            submissions_by_assignment = {}
            for submission in all_submissions:
                assignment_id = str(submission.get("assignment_id", ""))
                if assignment_id:
                    submissions_by_assignment[assignment_id] = submission

            results = {
                "assignments_processed": 0,
                "assignments_created": 0,
                "assignments_updated": 0,
                "categories_created": len(group_mapping),
            }

            # Process each assignment with bulk submissions data (no flush per assignment)
            logger.info(f"  Processing {len(canvas_assignments)} assignments...")
            for canvas_assignment in canvas_assignments:
                try:
                    canvas_assignment_id = str(canvas_assignment["id"])
                    submission = submissions_by_assignment.get(canvas_assignment_id)

                    assignment_result = self._sync_assignment(
                        canvas_assignment,
                        canvas_course_id,
                        local_course_id,
                        group_mapping,
                        submission,  # Pass pre-fetched submission
                        flush=False,  # Don't flush per assignment, batch them
                    )

                    results["assignments_processed"] += 1
                    if assignment_result["created"]:
                        results["assignments_created"] += 1
                    else:
                        results["assignments_updated"] += 1

                except Exception as e:
                    logger.error(
                        f"Failed to sync assignment {canvas_assignment.get('name', 'Unknown')}: {e}"
                    )

            # Single flush for all assignments
            if results["assignments_processed"] > 0:
                _ensure_models()

                db.session.flush()
                logger.info(
                    f"  Successfully flushed {results['assignments_processed']} assignments"
                )

            logger.info(f"  Course sync results: {results}")
            return results

        except Exception as e:
            logger.error(
                f"Failed to sync assignments for course {canvas_course_id}: {e}"
            )
            return {
                "assignments_processed": 0,
                "assignments_created": 0,
                "assignments_updated": 0,
                "categories_created": 0,
            }

    def _create_assignment_groups(
        self, canvas_groups: List[Dict[str, Any]], local_course_id: int
    ) -> Dict[str, int]:
        """
        Create local assignment groups from Canvas assignment groups

        Args:
            canvas_groups: List of Canvas assignment groups
            local_course_id: Local course ID

        Returns:
            Dict mapping Canvas group ID to local category ID
        """
        _ensure_models()

        group_mapping = {}
        new_categories = []

        # First pass: identify existing categories and prepare new ones
        for canvas_group in canvas_groups:
            canvas_group_id = str(canvas_group["id"])
            group_name = canvas_group.get("name", "Unnamed Category")
            group_weight = (
                canvas_group.get("group_weight", 0) / 100.0
            )  # Convert percentage to decimal

            # Check if category already exists
            existing_category = GradeCategory.query.filter_by(
                course_id=local_course_id, name=group_name
            ).first()

            if not existing_category:
                # Create new category object (don't add to session yet)
                category = GradeCategory(
                    name=group_name, weight=group_weight, course_id=local_course_id
                )
                new_categories.append((canvas_group_id, category))
                logger.info(f"Preparing to create assignment category: {group_name}")
            else:
                # Update weight if different
                if existing_category.weight != group_weight:
                    existing_category.weight = group_weight
                group_mapping[canvas_group_id] = existing_category.id

        # Batch add new categories and flush once
        if new_categories:
            for canvas_group_id, category in new_categories:
                db.session.add(category)

            # Single flush for all new categories
            db.session.flush()

            # Map canvas group IDs to new category IDs
            for canvas_group_id, category in new_categories:
                group_mapping[canvas_group_id] = category.id

            logger.info(f"Created {len(new_categories)} assignment categories in batch")

        return group_mapping

    def _sync_assignment(
        self,
        canvas_assignment: Dict[str, Any],
        canvas_course_id: str,
        local_course_id: int,
        group_mapping: Dict[str, int],
        submission: Optional[Dict[str, Any]] = None,
        flush: bool = False,
    ) -> Dict[str, bool]:
        """
        Sync a single assignment

        Args:
            canvas_assignment: Canvas assignment data
            canvas_course_id: Canvas course ID
            local_course_id: Local course ID
            group_mapping: Mapping of Canvas group IDs to local category IDs
            submission: Pre-fetched submission data (optional, for bulk sync optimization)
            flush: Whether to flush immediately (default: False for batch operations)

        Returns:
            Dict with sync result
        """
        _ensure_models()

        canvas_assignment_id = str(canvas_assignment["id"])
        assignment_name = canvas_assignment.get("name", "Unnamed Assignment")
        max_score = float(canvas_assignment.get("points_possible", 0))
        due_date = None

        logger.debug(
            f"Syncing assignment {assignment_name} (ID: {canvas_assignment_id}) "
            f"for course {canvas_course_id}"
        )

        # Parse due date
        if canvas_assignment.get("due_at"):
            try:
                from datetime import timezone, timedelta

                # Parse the UTC datetime from Canvas API
                # Canvas API returns dates in UTC (e.g., "2024-11-14T07:59:00Z")
                # This represents 11:59pm PST on Nov 13 (PST is UTC-8)
                due_date_utc = datetime.fromisoformat(
                    canvas_assignment["due_at"].replace("Z", "+00:00")
                )

                # Convert from UTC to PST/PDT (Pacific Time, UTC-8 / UTC-7)
                # For simplicity, using PST (UTC-8). In production, use pytz for proper timezone handling.
                pacific_offset = timedelta(hours=-8)  # PST is UTC-8
                pacific_tz = timezone(pacific_offset)
                due_date_pacific = due_date_utc.astimezone(pacific_tz)

                # Convert to naive datetime to prevent MySQL from doing additional timezone conversion
                due_date = due_date_pacific.replace(tzinfo=None)
                logger.debug(
                    f"Converted due date from UTC {due_date_utc} to local {due_date}"
                )
            except ValueError as e:
                logger.warning(
                    f"Could not parse due date for assignment {assignment_name}: {e}"
                )

        # Get category ID if assignment group is specified
        category_id = None
        if canvas_assignment.get("assignment_group_id"):
            canvas_group_id = str(canvas_assignment["assignment_group_id"])
            category_id = group_mapping.get(canvas_group_id)
            logger.debug(
                f"Assignment {assignment_name} mapped to category {category_id}"
            )

        # Find or create local assignment
        local_assignment = Assignment.query.filter_by(
            canvas_assignment_id=canvas_assignment_id, course_id=local_course_id
        ).first()

        assignment_created = False
        if not local_assignment:
            # Create new assignment
            local_assignment = Assignment(
                name=assignment_name,
                max_score=max_score,
                course_id=local_course_id,
                category_id=category_id,
                due_date=due_date,
                canvas_assignment_id=canvas_assignment_id,
                canvas_course_id=canvas_course_id,
                completed=False,
                is_extra_credit=False,
            )
            db.session.add(local_assignment)
            assignment_created = True
            logger.debug(f"Prepared new assignment: {assignment_name}")
            log_canvas_db_operation(
                "create",
                "Assignment",
                count=1,
                course_id=local_course_id,
                max_score=max_score,
            )
        else:
            # Update existing assignment
            local_assignment.name = assignment_name
            local_assignment.max_score = max_score
            local_assignment.due_date = due_date
            local_assignment.category_id = category_id
            logger.debug(f"Updated assignment: {assignment_name}")
            log_canvas_db_operation(
                "update",
                "Assignment",
                count=1,
                course_id=local_course_id,
            )

        # Use pre-fetched submission if provided, otherwise fetch it
        if submission is None:
            # Fallback to individual fetch (less efficient, only for backwards compatibility)
            try:
                submissions = self.canvas_api.get_submissions(
                    canvas_course_id, canvas_assignment_id
                )
                if submissions and len(submissions) > 0:
                    submission = submissions[0]
                    logger.debug(f"Fetched submission for assignment {assignment_name}")
            except Exception as e:
                logger.warning(
                    f"Could not fetch submission for assignment {assignment_name}: {e}"
                )

        # Apply submission data if available
        if submission:
            workflow_state = submission.get("workflow_state", "unsubmitted")
            logger.debug(
                f"Assignment {assignment_name} submission state: {workflow_state}"
            )

            # Track submission status
            # Canvas workflow_state values: 'unsubmitted', 'submitted', 'graded', 'pending_review'
            local_assignment.is_submitted = workflow_state in [
                "submitted",
                "graded",
                "pending_review",
            ]

            # Set completed=True if submitted OR graded
            # This ensures submitted work shows as completed even before grading
            local_assignment.completed = local_assignment.is_submitted

            # Apply score if available
            if submission.get("score") is not None:
                local_assignment.score = float(submission["score"])
                logger.debug(
                    f"Assignment {assignment_name} score: {local_assignment.score}"
                )

            # Capture missing status from Canvas
            local_assignment.is_missing = submission.get("missing", False)
        else:
            # No submission data - mark as not submitted and not completed
            local_assignment.is_submitted = False
            local_assignment.completed = False
            logger.debug(f"No submission data for assignment {assignment_name}")

        local_assignment.last_synced_canvas = datetime.utcnow()

        # Only flush if explicitly requested (normally batched)
        if flush:
            db.session.flush()
            logger.debug(f"Flushed assignment {assignment_name} to database")

        return {"created": assignment_created}


def create_canvas_sync_service(
    user, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
):
    """
    Factory function to create Canvas sync service for a user

    Args:
        user: User instance
        progress_callback: Optional callback function for progress updates

    Returns:
        CanvasSyncService instance
    """
    from .canvas_api_service import CanvasAPIService

    if not user.canvas_base_url or not user.canvas_access_token:
        raise CanvasSyncError("User Canvas credentials not configured")

    canvas_api = CanvasAPIService(
        base_url=user.canvas_base_url, access_token=user.canvas_access_token
    )

    return CanvasSyncService(user, canvas_api, progress_callback)
