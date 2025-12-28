#!/usr/bin/env python3
"""
Canvas Sync Log Analysis Tool

This script parses and analyzes Canvas sync logs to provide:
- Summary statistics
- Performance metrics
- Error analysis
- Timing analysis
- Course processing details
"""

import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any


class CanvasLogAnalyzer:
    """Analyze Canvas sync logs and generate reports."""

    def __init__(self, log_dir: str = "./logs/canvas_sync"):
        """Initialize analyzer with log directory."""
        self.log_dir = Path(log_dir)
        self.logs = {
            "operations": self.log_dir / "operations.log",
            "api_calls": self.log_dir / "api_calls.log",
            "database": self.log_dir / "database.log",
            "errors": self.log_dir / "errors.log",
            "progress": self.log_dir / "progress.log",
        }

    def read_log_file(self, log_type: str) -> List[str]:
        """Read a log file and return lines."""
        log_file = self.logs.get(log_type)
        if not log_file or not log_file.exists():
            return []

        try:
            with open(log_file, "r") as f:
                return f.readlines()
        except Exception as e:
            print(f"Error reading {log_type} log: {e}")
            return []

    def parse_timestamp(self, line: str) -> str:
        """Extract timestamp from log line."""
        match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
        return match.group(1) if match else None

    def analyze_operations(self) -> Dict[str, Any]:
        """Analyze operations log."""
        lines = self.read_log_file("operations")
        if not lines:
            return {"status": "No operations log found"}

        analysis = {
            "total_lines": len(lines),
            "sync_tasks": [],
            "connections_tested": 0,
            "courses_processed": 0,
            "assignments_synced": 0,
            "total_elapsed_time": 0,
            "timestamps": [],
        }

        for line in lines:
            ts = self.parse_timestamp(line)
            if ts:
                analysis["timestamps"].append(ts)

            # Count sync task starts
            if "task_id:" in line and "sync_canvas_data_task" in line:
                task_match = re.search(r"task_id: ([a-f0-9\-]+)", line)
                if task_match:
                    analysis["sync_tasks"].append(
                        {"task_id": task_match.group(1), "timestamp": ts}
                    )

            # Count connection tests
            if "Canvas connection test" in line:
                analysis["connections_tested"] += 1

            # Count courses
            if "Processing course:" in line:
                analysis["courses_processed"] += 1

            # Count assignments
            if "assignments_synced:" in line:
                match = re.search(r"assignments_synced: (\d+)", line)
                if match:
                    analysis["assignments_synced"] += int(match.group(1))

            # Extract elapsed time
            if "elapsed_time_seconds:" in line:
                match = re.search(r"elapsed_time_seconds: ([\d.]+)", line)
                if match:
                    analysis["total_elapsed_time"] += float(match.group(1))

        return analysis

    def analyze_api_calls(self) -> Dict[str, Any]:
        """Analyze API calls log."""
        lines = self.read_log_file("api_calls")
        if not lines:
            return {"status": "No API calls log found"}

        analysis = {
            "total_calls": 0,
            "by_method": Counter(),
            "by_endpoint": Counter(),
            "status_codes": Counter(),
            "total_duration_ms": 0,
            "error_codes": [],
            "paginated_requests": 0,
        }

        for line in lines:
            analysis["total_calls"] += 1

            # Count by HTTP method
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                if f" {method} " in line:
                    analysis["by_method"][method] += 1
                    break

            # Extract status code
            status_match = re.search(r"status_code: (\d+)", line)
            if status_match:
                status = status_match.group(1)
                analysis["status_codes"][status] += 1
                if status.startswith("4") or status.startswith("5"):
                    analysis["error_codes"].append(status)

            # Extract duration
            duration_match = re.search(r"duration_ms: ([\d.]+)", line)
            if duration_match:
                analysis["total_duration_ms"] += float(duration_match.group(1))

            # Count paginated requests
            if "pages:" in line:
                analysis["paginated_requests"] += 1

        return analysis

    def analyze_database(self) -> Dict[str, Any]:
        """Analyze database operations log."""
        lines = self.read_log_file("database")
        if not lines:
            return {"status": "No database log found"}

        analysis = {
            "total_operations": len(lines),
            "by_operation": Counter(),
            "by_entity": Counter(),
            "total_records_affected": 0,
            "courses_synced": 0,
            "batch_operations": 0,
        }

        for line in lines:
            # Count by operation type
            for op in ["create", "update", "delete", "sync"]:
                if f"operation: {op}" in line:
                    analysis["by_operation"][op] += 1
                    break

            # Count by entity type
            for entity in ["Course", "Assignment", "GradeCategory", "Submission"]:
                if f"entity_type: {entity}" in line:
                    analysis["by_entity"][entity] += 1
                    break

            # Extract record count
            count_match = re.search(r"count: (\d+)", line)
            if count_match:
                analysis["total_records_affected"] += int(count_match.group(1))

            # Count course syncs
            if "course_id:" in line:
                analysis["courses_synced"] += 1

            # Count batch operations
            if "batch_operation: true" in line:
                analysis["batch_operations"] += 1

        return analysis

    def analyze_errors(self) -> Dict[str, Any]:
        """Analyze errors log."""
        lines = self.read_log_file("errors")
        if not lines:
            return {"status": "No errors found", "total_errors": 0}

        analysis = {
            "total_errors": len(lines),
            "by_type": Counter(),
            "by_user": Counter(),
            "by_course": Counter(),
            "error_messages": [],
            "recent_errors": [],
        }

        for line in lines:
            analysis["by_type"]["general"] += 1

            # Extract error type
            if "error_type:" in line:
                type_match = re.search(r"error_type: (\w+)", line)
                if type_match:
                    analysis["by_type"][type_match.group(1)] += 1

            # Extract user_id
            if "user_id:" in line:
                user_match = re.search(r"user_id: (\d+)", line)
                if user_match:
                    analysis["by_user"][user_match.group(1)] += 1

            # Extract course_id
            if "course_id:" in line:
                course_match = re.search(r"course_id: (\d+)", line)
                if course_match:
                    analysis["by_course"][course_match.group(1)] += 1

            # Store recent errors (last 5)
            ts = self.parse_timestamp(line)
            if len(analysis["recent_errors"]) < 5:
                analysis["recent_errors"].append(
                    {"timestamp": ts, "message": line[:200]}
                )

        return analysis

    def analyze_progress(self) -> Dict[str, Any]:
        """Analyze progress log."""
        lines = self.read_log_file("progress")
        if not lines:
            return {"status": "No progress log found"}

        analysis = {
            "total_entries": len(lines),
            "tasks": defaultdict(lambda: {"max_progress": 0, "items": []}),
        }

        for line in lines:
            # Extract task_id
            task_match = re.search(r"task_id: ([a-f0-9\-]+)", line)
            if task_match:
                task_id = task_match.group(1)

                # Extract progress percentage
                prog_match = re.search(r"progress: (\d+)%", line)
                if prog_match:
                    progress = int(prog_match.group(1))
                    analysis["tasks"][task_id]["max_progress"] = max(
                        analysis["tasks"][task_id]["max_progress"], progress
                    )

                # Store line info
                ts = self.parse_timestamp(line)
                analysis["tasks"][task_id]["items"].append(
                    {"timestamp": ts, "line": line[:150]}
                )

        return analysis

    def generate_report(self) -> str:
        """Generate comprehensive analysis report."""
        report = []
        report.append("=" * 80)
        report.append("CANVAS SYNC LOG ANALYSIS REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")

        # Operations analysis
        report.append("📊 OPERATIONS SUMMARY")
        report.append("-" * 80)
        ops = self.analyze_operations()
        if "status" not in ops:
            report.append(f"Total Operations Log Lines: {ops.get('total_lines', 0)}")
            report.append(f"Sync Tasks Started: {len(ops.get('sync_tasks', []))}")
            report.append(
                f"Canvas Connections Tested: {ops.get('connections_tested', 0)}"
            )
            report.append(f"Courses Processed: {ops.get('courses_processed', 0)}")
            report.append(
                f"Total Assignments Synced: {ops.get('assignments_synced', 0)}"
            )
            report.append(
                f"Total Elapsed Time: {ops.get('total_elapsed_time', 0):.2f} seconds"
            )
            if ops.get("sync_tasks"):
                report.append(
                    f"Time Range: {ops.get('timestamps', ['N/A'])[0]} - {ops.get('timestamps', ['N/A'])[-1]}"
                )
        else:
            report.append(ops["status"])
        report.append("")

        # API analysis
        report.append("🌐 API CALLS ANALYSIS")
        report.append("-" * 80)
        api = self.analyze_api_calls()
        if "status" not in api:
            report.append(f"Total API Calls: {api.get('total_calls', 0)}")
            if api.get("by_method"):
                report.append("By HTTP Method:")
                for method, count in sorted(api["by_method"].items()):
                    report.append(f"  {method}: {count}")
            report.append(
                f"Total Request Duration: {api.get('total_duration_ms', 0):.2f} ms"
            )
            if api.get("total_calls"):
                avg_time = api.get("total_duration_ms", 0) / api.get("total_calls", 1)
                report.append(f"Average Request Time: {avg_time:.2f} ms")
            report.append(f"Paginated Requests: {api.get('paginated_requests', 0)}")
            if api.get("status_codes"):
                report.append("Status Codes:")
                for code, count in sorted(api["status_codes"].items()):
                    report.append(f"  {code}: {count}")
        else:
            report.append(api["status"])
        report.append("")

        # Database analysis
        report.append("💾 DATABASE OPERATIONS ANALYSIS")
        report.append("-" * 80)
        db = self.analyze_database()
        if "status" not in db:
            report.append(f"Total Database Operations: {db.get('total_operations', 0)}")
            if db.get("by_operation"):
                report.append("By Operation Type:")
                for op, count in sorted(db["by_operation"].items()):
                    report.append(f"  {op}: {count}")
            report.append(
                f"Total Records Affected: {db.get('total_records_affected', 0)}"
            )
            if db.get("by_entity"):
                report.append("By Entity Type:")
                for entity, count in sorted(db["by_entity"].items()):
                    report.append(f"  {entity}: {count}")
            report.append(f"Batch Operations: {db.get('batch_operations', 0)}")
        else:
            report.append(db["status"])
        report.append("")

        # Error analysis
        report.append("⚠️  ERROR ANALYSIS")
        report.append("-" * 80)
        errors = self.analyze_errors()
        report.append(f"Total Errors: {errors.get('total_errors', 0)}")
        if errors.get("total_errors", 0) > 0:
            if errors.get("by_user"):
                report.append("Errors by User ID (Top 5):")
                for user, count in errors["by_user"].most_common(5):
                    report.append(f"  User {user}: {count} errors")
            if errors.get("by_course"):
                report.append("Errors by Course ID (Top 5):")
                for course, count in errors["by_course"].most_common(5):
                    report.append(f"  Course {course}: {count} errors")
            if errors.get("recent_errors"):
                report.append("Recent Errors (Last 5):")
                for err in errors["recent_errors"]:
                    report.append(f"  {err['timestamp']}: {err['message']}")
        report.append("")

        # Progress analysis
        report.append("📈 PROGRESS ANALYSIS")
        report.append("-" * 80)
        progress = self.analyze_progress()
        if "status" not in progress:
            report.append(f"Total Progress Entries: {progress.get('total_entries', 0)}")
            if progress.get("tasks"):
                report.append(f"Active Tasks: {len(progress['tasks'])}")
                for task_id, task_data in list(progress["tasks"].items())[:5]:
                    report.append(
                        f"  Task {task_id[:8]}...: Max Progress {task_data['max_progress']}%"
                    )
        report.append("")

        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)

        return "\n".join(report)

    def export_json(self, output_file: str = None) -> str:
        """Export analysis as JSON."""
        if output_file is None:
            output_file = (
                f"canvas_logs_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        analysis = {
            "generated_at": datetime.now().isoformat(),
            "operations": self.analyze_operations(),
            "api_calls": self.analyze_api_calls(),
            "database": self.analyze_database(),
            "errors": self.analyze_errors(),
            "progress": self.analyze_progress(),
        }

        with open(output_file, "w") as f:
            json.dump(analysis, f, indent=2, default=str)

        return output_file


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Canvas sync logs")
    parser.add_argument(
        "--log-dir",
        default="./logs/canvas_sync",
        help="Path to logs directory (default: ./logs/canvas_sync)",
    )
    parser.add_argument("--json", action="store_true", help="Export analysis as JSON")
    parser.add_argument("--output", help="Output file for JSON export")

    args = parser.parse_args()

    analyzer = CanvasLogAnalyzer(args.log_dir)

    if args.json:
        output = analyzer.export_json(args.output)
        print(f"Analysis exported to: {output}")
    else:
        report = analyzer.generate_report()
        print(report)


if __name__ == "__main__":
    main()
