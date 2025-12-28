"""
Canvas REST API Service

This service handles communication with Canvas LMS REST API for fetching
courses, assignments, and grades.
"""

import requests
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Import canvas sync logging utilities
try:
    from app.logging_config import log_canvas_api_call
except ImportError:
    # Fallback if logging config not available
    def log_canvas_api_call(*args, **kwargs):
        pass


class CanvasAPIError(Exception):
    """Custom exception for Canvas API errors"""

    pass


class CanvasAPIService:
    """
    Service for interacting with Canvas LMS REST API

    Provides methods to:
    - Authenticate with Canvas API using access tokens
    - Fetch user's courses
    - Fetch assignments and submissions for courses
    - Handle pagination and rate limiting
    """

    def __init__(self, base_url: str, access_token: str):
        """
        Initialize Canvas API service

        Args:
            base_url: Canvas instance base URL (e.g., 'https://canvas.university.edu')
            access_token: Canvas personal access token or OAuth token
        """
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.access_token = access_token
        self.session = requests.Session()

        # Configure connection pooling and retry strategy
        retry_strategy = Retry(
            total=5,  # Increased from 3 to 5 retries
            backoff_factor=2,  # Exponential backoff
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,  # Don't raise on status codes in the list
        )
        adapter = HTTPAdapter(
            pool_connections=10, pool_maxsize=20, max_retries=retry_strategy
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json+canvas-string-ids",  # Ensure IDs are strings
            }
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make authenticated request to Canvas API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to /api/v1)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            CanvasAPIError: If request fails
        """
        url = urljoin(f"{self.api_base}/", endpoint.lstrip("/"))

        request_start = time.time()
        try:
            logger.debug(f"Making Canvas API request: {method} {endpoint}")
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            duration_ms = (time.time() - request_start) * 1000
            logger.debug(
                f"Canvas API response: {method} {endpoint} - Status: {response.status_code} - Duration: {duration_ms:.1f}ms"
            )
            log_canvas_api_call(
                method,
                endpoint,
                response_status=response.status_code,
                duration_ms=round(duration_ms, 1),
                url=url,
            )
            return response
        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - request_start) * 1000
            logger.error(
                f"Canvas API request failed: {method} {url} - {e} - Duration: {duration_ms:.1f}ms"
            )
            log_canvas_api_call(
                method,
                endpoint,
                response_status=getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None,
                duration_ms=round(duration_ms, 1),
                error=str(e),
            )
            raise CanvasAPIError(f"API request failed: {e}")

    def _get_paginated_data(
        self, endpoint: str, params: Optional[Dict] = None, concurrent: bool = True
    ) -> List[Dict]:
        """
        Fetch all pages of data from a paginated endpoint

        Args:
            endpoint: API endpoint
            params: Query parameters
            concurrent: Whether to fetch pages concurrently (default: True)

        Returns:
            List of all items from all pages
        """
        all_data = []
        params = params or {}
        params["per_page"] = 100  # Maximum items per page

        logger.debug(f"Fetching paginated data from {endpoint} with params: {params}")

        # Fetch first page to get pagination info
        response = self._make_request("GET", endpoint, params=params)
        data = response.json()

        if isinstance(data, list):
            all_data.extend(data)
        else:
            all_data.append(data)

        logger.debug(f"First page returned {len(all_data)} items")

        # Extract all page URLs from Link header
        page_urls = []
        if "Link" in response.headers:
            page_urls = self._extract_page_urls(response.headers["Link"])

        logger.debug(f"Found {len(page_urls)} additional pages to fetch")

        # If no more pages, return early
        if not page_urls:
            logger.debug(
                f"Pagination complete: Total {len(all_data)} items from endpoint {endpoint}"
            )
            log_canvas_api_call("GET", endpoint, count=len(all_data), pages=1)
            return all_data

        # Fetch remaining pages concurrently or sequentially
        if concurrent and len(page_urls) > 1:
            logger.debug(f"Fetching {len(page_urls)} pages concurrently")
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {
                    executor.submit(self._fetch_page, url): url for url in page_urls
                }
                for future in as_completed(future_to_url):
                    try:
                        page_data = future.result()
                        if isinstance(page_data, list):
                            all_data.extend(page_data)
                        else:
                            all_data.append(page_data)
                    except Exception as e:
                        logger.error(
                            f"Failed to fetch page {future_to_url[future]}: {e}"
                        )
        else:
            # Sequential fetching for single page or if concurrent disabled
            logger.debug(f"Fetching {len(page_urls)} pages sequentially")
            for url in page_urls:
                try:
                    page_data = self._fetch_page(url)
                    if isinstance(page_data, list):
                        all_data.extend(page_data)
                    else:
                        all_data.append(page_data)
                except Exception as e:
                    logger.error(f"Failed to fetch page {url}: {e}")

        logger.info(
            f"Pagination complete: Total {len(all_data)} items from endpoint {endpoint} ({len(page_urls) + 1} pages)"
        )
        log_canvas_api_call(
            "GET", endpoint, count=len(all_data), pages=len(page_urls) + 1
        )
        return all_data

    def _extract_page_urls(self, link_header: str) -> List[str]:
        """
        Extract all page URLs from Link header (except first which we already have)

        Args:
            link_header: Link header from response

        Returns:
            List of page URLs
        """
        page_urls = []
        current_url = None

        for link in link_header.split(","):
            link = link.strip()
            if 'rel="next"' in link:
                url = link.split("<")[1].split(">")[0]
                # Remove base URL to get relative endpoint
                url = url.replace(self.api_base, "")
                current_url = url
                page_urls.append(url)

        # Continue following next links to get all page URLs
        while current_url:
            try:
                response = self._make_request("GET", current_url)
                current_url = None

                if "Link" in response.headers:
                    links = response.headers["Link"]
                    for link in links.split(","):
                        if 'rel="next"' in link:
                            url = link.split("<")[1].split(">")[0]
                            url = url.replace(self.api_base, "")
                            if url not in page_urls:
                                page_urls.append(url)
                                current_url = url
                            break
            except Exception as e:
                logger.error(f"Failed to extract page URLs: {e}")
                break

        return page_urls

    def _fetch_page(self, url: str) -> Any:
        """
        Fetch a single page of data

        Args:
            url: Page URL (relative to api_base)

        Returns:
            Page data
        """
        response = self._make_request("GET", url)
        return response.json()

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the Canvas API connection

        Returns:
            Dict with connection status and user info
        """
        try:
            response = self._make_request("GET", "/users/self")
            user_data = response.json()
            return {
                "success": True,
                "user": user_data,
                "message": f"Connected as {user_data.get('name', 'Unknown')}",
            }
        except CanvasAPIError as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to connect to Canvas API",
            }

    def get_courses(
        self, enrollment_state: str = "active", since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's courses

        Args:
            enrollment_state: Filter by enrollment state (active, completed, etc.)
            since: Only fetch courses updated since this datetime (for incremental sync)

        Returns:
            List of course dictionaries
        """
        params = {
            "enrollment_state": enrollment_state,
            "include": ["total_scores", "current_grading_period_scores", "term"],
        }

        # Add incremental sync support
        if since:
            params["updated_since"] = since.isoformat()
            logger.info(f"Fetching courses updated since {since}")

        try:
            logger.info(f"Fetching {enrollment_state} courses from Canvas API")
            courses = self._get_paginated_data("/courses", params)
            logger.info(
                f"Fetched {len(courses)} courses from Canvas{' (incremental)' if since else ''}"
            )
            log_canvas_api_call(
                "GET",
                "/courses",
                response_status=200,
                count=len(courses),
                incremental=since is not None,
            )
            return courses
        except CanvasAPIError as e:
            logger.error(f"Failed to fetch courses: {e}")
            raise

    def get_assignments(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get assignments for a specific course

        Args:
            course_id: Canvas course ID

        Returns:
            List of assignment dictionaries
        """
        params = {"include": ["submission", "score_statistics", "rubric_assessment"]}

        try:
            logger.info(f"Fetching assignments for course {course_id}")
            assignments = self._get_paginated_data(
                f"/courses/{course_id}/assignments", params
            )
            logger.info(
                f"Fetched {len(assignments)} assignments from course {course_id}"
            )
            log_canvas_api_call(
                "GET",
                f"/courses/{course_id}/assignments",
                response_status=200,
                count=len(assignments),
            )
            return assignments
        except CanvasAPIError as e:
            logger.error(f"Failed to fetch assignments for course {course_id}: {e}")
            raise

    def get_submissions(
        self, course_id: str, assignment_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get submissions for a course or specific assignment

        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID (optional, gets all if not specified)

        Returns:
            List of submission dictionaries
        """
        if assignment_id:
            # Get single assignment submission
            endpoint = (
                f"/courses/{course_id}/assignments/{assignment_id}/submissions/self"
            )
            try:
                logger.debug(
                    f"Fetching submission for assignment {assignment_id} in course {course_id}"
                )
                response = self._make_request("GET", endpoint)
                submission = response.json()
                log_canvas_api_call(
                    "GET",
                    endpoint,
                    response_status=response.status_code,
                )
                return [submission] if submission else []
            except CanvasAPIError as e:
                logger.error(
                    f"Failed to fetch submission for assignment {assignment_id}: {e}"
                )
                raise
        else:
            # Get all submissions for the user in this course (BULK - more efficient)
            endpoint = f"/courses/{course_id}/students/submissions"
            params = {
                "student_ids": ["self"],
                "include": ["assignment", "submission_history", "rubric_assessment"],
            }

            try:
                logger.info(f"Fetching all submissions for course {course_id}")
                submissions = self._get_paginated_data(endpoint, params)
                logger.info(
                    f"Fetched {len(submissions)} submissions from course {course_id} (bulk)"
                )
                log_canvas_api_call(
                    "GET",
                    endpoint,
                    response_status=200,
                    count=len(submissions),
                    bulk=True,
                )
                return submissions
            except CanvasAPIError as e:
                logger.error(f"Failed to fetch submissions for course {course_id}: {e}")
                raise

    def get_assignment_groups(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get assignment groups (categories) for a course

        Args:
            course_id: Canvas course ID

        Returns:
            List of assignment group dictionaries
        """
        params = {"include": ["assignments"]}

        try:
            groups = self._get_paginated_data(
                f"/courses/{course_id}/assignment_groups", params
            )
            logger.info(
                f"Fetched {len(groups)} assignment groups from course {course_id}"
            )
            return groups
        except CanvasAPIError as e:
            logger.error(
                f"Failed to fetch assignment groups for course {course_id}: {e}"
            )
            raise

    def get_course_details(self, course_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific course

        Args:
            course_id: Canvas course ID

        Returns:
            Course dictionary with detailed information
        """
        params = {"include": ["term", "course_progress", "total_scores"]}

        try:
            response = self._make_request("GET", f"/courses/{course_id}", params=params)
            course = response.json()
            logger.info(f"Fetched details for course {course_id}")
            return course
        except CanvasAPIError as e:
            logger.error(f"Failed to fetch course details for {course_id}: {e}")
            raise


def create_canvas_api_service(base_url: str, access_token: str) -> CanvasAPIService:
    """
    Factory function to create Canvas API service instance

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas access token

    Returns:
        CanvasAPIService instance
    """
    return CanvasAPIService(base_url, access_token)
