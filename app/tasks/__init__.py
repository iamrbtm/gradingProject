"""
Background Task Modules
======================

This package contains Celery tasks for background processing including:
- ML model training and updates
- Analytics computations
- Report generation
- Data maintenance

Author: Analytics Team
Date: 2024-12-19
"""

# Task module imports for easy access
from . import ml
from . import analytics
from . import exports
from . import notifications
from . import canvas_sync

__all__ = ["ml", "analytics", "exports", "notifications", "canvas_sync"]
