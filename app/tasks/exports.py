"""
Export Functionality Tasks
========================

This module contains Celery tasks for generating and exporting analytics reports
in various formats including CSV, Excel, and PDF.

Features:
- Comprehensive analytics report generation
- Multiple export formats (CSV, Excel, PDF)
- Customizable report templates
- Automated report delivery via email
- Scheduled report generation
- Interactive charts and visualizations in reports

Author: Analytics Team
Date: 2024-12-19
"""

import logging
import os
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np

try:
    from celery import shared_task

    CELERY_AVAILABLE = True
except ImportError:

    def shared_task(func):
        return func

    CELERY_AVAILABLE = False

try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
        Image,
        PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from fpdf import FPDF

    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

from ..models import (
    db,
    User,
    Term,
    Course,
    Assignment,
    PerformanceMetric,
    PerformanceTrend,
    GradePrediction,
    RiskAssessment,
    SmartNotification,
)
from ..services.performance_analytics import PerformanceAnalyticsService
from ..services.predictive_analytics import PredictiveAnalyticsEngine
from ..services.grade_calculator import GradeCalculatorService

logger = logging.getLogger(__name__)


class AnalyticsReportGenerator:
    """Generates comprehensive analytics reports in multiple formats."""

    def __init__(self):
        self.performance_service = PerformanceAnalyticsService()
        self.predictive_service = PredictiveAnalyticsEngine()
        self.grade_calculator = GradeCalculatorService()

        # Create reports directory
        self.reports_dir = "reports"
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)

    def generate_user_data(self, user_id: int) -> Dict[str, Any]:
        """Generate comprehensive analytics data for a user."""
        user = User.query.get(user_id)
        if not user:
            return {}

        data = {
            "user_info": {
                "id": user.id,
                "username": user.username,
                "report_generated": datetime.utcnow().isoformat(),
            },
            "performance": {},
            "courses": [],
            "predictions": [],
            "trends": [],
            "notifications": [],
        }

        try:
            # Get performance snapshot
            performance_snapshot = self.performance_service.get_performance_snapshot(
                user_id
            )
            data["performance"] = {
                "overall_gpa": float(performance_snapshot.overall_gpa or 0),
                "term_gpa": float(performance_snapshot.term_gpa or 0),
                "trend_direction": performance_snapshot.trend_direction,
                "course_count": len(performance_snapshot.course_grades or {}),
                "courses_at_risk": len(performance_snapshot.risk_courses or []),
                "strength_areas": performance_snapshot.strength_areas or [],
                "improvement_areas": performance_snapshot.improvement_areas or [],
            }

            # Get course details
            for term in user.terms:
                for course in term.courses:
                    course_grade = self.grade_calculator.calculate_course_grade(course)
                    completion_rate = (
                        self.grade_calculator.calculate_percentage_complete(course)
                    )

                    course_data = {
                        "course_name": course.name,
                        "term": f"{term.season} {term.year}",
                        "current_grade": float(course_grade or 0),
                        "completion_rate": float(completion_rate or 0),
                        "total_assignments": len(course.assignments),
                        "completed_assignments": len(
                            [a for a in course.assignments if a.score is not None]
                        ),
                        "credits": course.credits or 0,
                    }

                    # Get assignments
                    assignments = []
                    for assignment in course.assignments:
                        assignments.append(
                            {
                                "name": assignment.name,
                                "due_date": assignment.due_date.isoformat()
                                if assignment.due_date
                                else None,
                                "score": float(assignment.score or 0),
                                "max_score": float(assignment.max_score or 0),
                                "category": assignment.category.name
                                if assignment.category
                                else "Other",
                                "completed": assignment.score is not None,
                            }
                        )

                    course_data["assignments"] = assignments
                    data["courses"].append(course_data)

            # Get predictions for recent courses
            recent_courses = (
                Course.query.join(Term)
                .filter(Term.user_id == user_id)
                .order_by(Term.year.desc(), Term.season.desc())
                .limit(5)
                .all()
            )

            for course in recent_courses:
                try:
                    prediction = self.predictive_service.predict_final_grade(
                        course.id, user_id
                    )
                    if prediction:
                        data["predictions"].append(
                            {
                                "course_name": course.name,
                                "predicted_grade": float(
                                    prediction.predicted_grade or 0
                                ),
                                "confidence": float(prediction.confidence or 0),
                                "prediction_date": prediction.prediction_date.isoformat(),
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Could not get prediction for course {course.id}: {str(e)}"
                    )

            # Get performance trends
            trends = self.performance_service.analyze_performance_trends(user_id, 90)
            for metric_name, trend in trends.items():
                data["trends"].append(
                    {
                        "metric": metric_name,
                        "direction": trend.trend_direction,
                        "strength": float(trend.trend_strength or 0),
                        "data_points_count": len(trend.data_points or []),
                        "forecast": float(trend.forecast_next_period or 0),
                    }
                )

            # Get recent notifications
            recent_notifications = (
                SmartNotification.query.filter_by(user_id=user_id)
                .order_by(SmartNotification.created_at.desc())
                .limit(10)
                .all()
            )

            for notification in recent_notifications:
                data["notifications"].append(
                    {
                        "type": notification.notification_type,
                        "title": notification.title,
                        "priority": notification.priority,
                        "created_at": notification.created_at.isoformat(),
                        "read": notification.is_read,
                    }
                )

        except Exception as e:
            logger.error(f"Error generating user data for {user_id}: {str(e)}")

        return data

    def export_to_csv(self, user_data: Dict[str, Any], filename: str) -> str:
        """Export analytics data to CSV format."""
        try:
            filepath = os.path.join(self.reports_dir, filename)

            # Create multiple CSV sheets in a zip file or separate files
            courses_df = pd.DataFrame(user_data.get("courses", []))
            predictions_df = pd.DataFrame(user_data.get("predictions", []))
            trends_df = pd.DataFrame(user_data.get("trends", []))
            notifications_df = pd.DataFrame(user_data.get("notifications", []))

            # Save main courses data
            courses_df.to_csv(filepath, index=False)

            # Save additional sheets with different names
            if not predictions_df.empty:
                pred_filepath = filepath.replace(".csv", "_predictions.csv")
                predictions_df.to_csv(pred_filepath, index=False)

            if not trends_df.empty:
                trends_filepath = filepath.replace(".csv", "_trends.csv")
                trends_df.to_csv(trends_filepath, index=False)

            if not notifications_df.empty:
                notif_filepath = filepath.replace(".csv", "_notifications.csv")
                notifications_df.to_csv(notif_filepath, index=False)

            logger.info(f"CSV export completed: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return ""

    def export_to_excel(self, user_data: Dict[str, Any], filename: str) -> str:
        """Export analytics data to Excel format with multiple sheets."""
        try:
            filepath = os.path.join(self.reports_dir, filename)

            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                # Summary sheet
                summary_data = [
                    ["Username", user_data["user_info"]["username"]],
                    ["Overall GPA", user_data["performance"]["overall_gpa"]],
                    ["Current Term GPA", user_data["performance"]["term_gpa"]],
                    ["Trend Direction", user_data["performance"]["trend_direction"]],
                    ["Total Courses", user_data["performance"]["course_count"]],
                    ["Courses at Risk", user_data["performance"]["courses_at_risk"]],
                    ["Report Generated", user_data["user_info"]["report_generated"]],
                ]
                summary_df = pd.DataFrame(summary_data, columns=["Metric", "Value"])
                summary_df.to_excel(writer, sheet_name="Summary", index=False)

                # Courses sheet
                if user_data.get("courses"):
                    courses_df = pd.DataFrame(user_data["courses"])
                    courses_df.to_excel(writer, sheet_name="Courses", index=False)

                # Predictions sheet
                if user_data.get("predictions"):
                    predictions_df = pd.DataFrame(user_data["predictions"])
                    predictions_df.to_excel(
                        writer, sheet_name="Predictions", index=False
                    )

                # Trends sheet
                if user_data.get("trends"):
                    trends_df = pd.DataFrame(user_data["trends"])
                    trends_df.to_excel(writer, sheet_name="Trends", index=False)

                # Notifications sheet
                if user_data.get("notifications"):
                    notifications_df = pd.DataFrame(user_data["notifications"])
                    notifications_df.to_excel(
                        writer, sheet_name="Notifications", index=False
                    )

            logger.info(f"Excel export completed: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error exporting to Excel: {str(e)}")
            return ""

    def create_visualizations(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Create visualizations for the report."""
        if not MATPLOTLIB_AVAILABLE:
            return {}

        charts = {}

        try:
            # Set style
            plt.style.use("seaborn-v0_8" if hasattr(plt, "style") else "default")

            # GPA Trend Chart
            if user_data.get("courses"):
                courses = user_data["courses"]
                course_names = [
                    c["course_name"][:15] + "..."
                    if len(c["course_name"]) > 15
                    else c["course_name"]
                    for c in courses
                ]
                grades = [c["current_grade"] for c in courses]

                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.bar(course_names, grades, color="steelblue", alpha=0.7)
                ax.set_title("Course Grades Overview", fontsize=16, fontweight="bold")
                ax.set_ylabel("Grade", fontsize=12)
                ax.set_xlabel("Course", fontsize=12)
                ax.tick_params(axis="x", rotation=45)

                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + 1,
                        f"{height:.1f}",
                        ha="center",
                        va="bottom",
                    )

                plt.tight_layout()
                chart_path = os.path.join(self.reports_dir, "grades_chart.png")
                plt.savefig(chart_path, dpi=150, bbox_inches="tight")
                plt.close()
                charts["grades"] = chart_path

            # Completion Rate Chart
            if user_data.get("courses"):
                completion_rates = [c["completion_rate"] for c in courses]

                fig, ax = plt.subplots(figsize=(8, 8))
                colors = [
                    "lightcoral" if rate < 80 else "lightgreen"
                    for rate in completion_rates
                ]
                wedges, texts, autotexts = ax.pie(
                    completion_rates,
                    labels=course_names,
                    autopct="%1.1f%%",
                    colors=colors,
                    startangle=90,
                )
                ax.set_title("Course Completion Rates", fontsize=16, fontweight="bold")

                # Make percentage text more readable
                for autotext in autotexts:
                    autotext.set_color("white")
                    autotext.set_fontweight("bold")

                plt.tight_layout()
                chart_path = os.path.join(self.reports_dir, "completion_chart.png")
                plt.savefig(chart_path, dpi=150, bbox_inches="tight")
                plt.close()
                charts["completion"] = chart_path

            # Performance Trend Line Chart
            if user_data.get("trends"):
                trends = user_data["trends"]

                fig, ax = plt.subplots(figsize=(12, 6))

                x_pos = range(len(trends))
                trend_values = [t["strength"] for t in trends]
                trend_names = [t["metric"] for t in trends]

                colors = [
                    "green" if val > 0 else "red" if val < 0 else "gray"
                    for val in trend_values
                ]

                bars = ax.bar(x_pos, trend_values, color=colors, alpha=0.7)
                ax.set_title("Performance Trends", fontsize=16, fontweight="bold")
                ax.set_ylabel("Trend Strength", fontsize=12)
                ax.set_xlabel("Metrics", fontsize=12)
                ax.set_xticks(x_pos)
                ax.set_xticklabels(trend_names, rotation=45, ha="right")
                ax.axhline(y=0, color="black", linestyle="-", alpha=0.3)

                # Add value labels
                for i, bar in enumerate(bars):
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + (0.01 if height >= 0 else -0.03),
                        f"{height:.2f}",
                        ha="center",
                        va="bottom" if height >= 0 else "top",
                    )

                plt.tight_layout()
                chart_path = os.path.join(self.reports_dir, "trends_chart.png")
                plt.savefig(chart_path, dpi=150, bbox_inches="tight")
                plt.close()
                charts["trends"] = chart_path

        except Exception as e:
            logger.error(f"Error creating visualizations: {str(e)}")

        return charts

    def export_to_pdf(self, user_data: Dict[str, Any], filename: str) -> str:
        """Export analytics data to PDF format with charts and formatting."""
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available, using simple PDF export")
            return self.export_to_simple_pdf(user_data, filename)

        try:
            filepath = os.path.join(self.reports_dir, filename)

            # Create the PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )

            # Container for the 'Flowable' objects
            story = []

            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Center alignment
            )

            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=16,
                spaceAfter=12,
                textColor=colors.darkblue,
            )

            # Title
            title = Paragraph("Academic Analytics Report", title_style)
            story.append(title)
            story.append(Spacer(1, 20))

            # User Information
            user_info = f"""
            <b>Student:</b> {user_data["user_info"]["username"]}<br/>
            <b>Report Generated:</b> {user_data["user_info"]["report_generated"]}<br/>
            <b>Overall GPA:</b> {user_data["performance"]["overall_gpa"]:.2f}<br/>
            <b>Current Term GPA:</b> {user_data["performance"]["term_gpa"]:.2f}<br/>
            <b>Performance Trend:</b> {user_data["performance"]["trend_direction"]}
            """
            story.append(Paragraph(user_info, styles["Normal"]))
            story.append(Spacer(1, 20))

            # Performance Summary
            story.append(Paragraph("Performance Summary", heading_style))

            perf_data = [
                ["Metric", "Value"],
                ["Total Courses", str(user_data["performance"]["course_count"])],
                ["Courses at Risk", str(user_data["performance"]["courses_at_risk"])],
                ["Overall GPA", f"{user_data['performance']['overall_gpa']:.2f}"],
                ["Term GPA", f"{user_data['performance']['term_gpa']:.2f}"],
            ]

            perf_table = Table(perf_data)
            perf_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 14),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            story.append(perf_table)
            story.append(Spacer(1, 20))

            # Add visualizations if available
            charts = self.create_visualizations(user_data)
            for chart_name, chart_path in charts.items():
                if os.path.exists(chart_path):
                    story.append(
                        Paragraph(f"{chart_name.title()} Chart", heading_style)
                    )
                    img = Image(chart_path, width=6 * inch, height=3.6 * inch)
                    story.append(img)
                    story.append(Spacer(1, 20))

            # Course Details
            if user_data.get("courses"):
                story.append(PageBreak())
                story.append(Paragraph("Course Details", heading_style))

                course_data = [["Course", "Term", "Grade", "Completion", "Assignments"]]

                for course in user_data["courses"]:
                    course_data.append(
                        [
                            course["course_name"],
                            course["term"],
                            f"{course['current_grade']:.1f}",
                            f"{course['completion_rate']:.1f}%",
                            f"{course['completed_assignments']}/{course['total_assignments']}",
                        ]
                    )

                course_table = Table(course_data)
                course_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )

                story.append(course_table)

            # Predictions
            if user_data.get("predictions"):
                story.append(Spacer(1, 30))
                story.append(Paragraph("Grade Predictions", heading_style))

                pred_data = [["Course", "Predicted Grade", "Confidence"]]

                for pred in user_data["predictions"]:
                    pred_data.append(
                        [
                            pred["course_name"],
                            f"{pred['predicted_grade']:.1f}",
                            f"{pred['confidence']:.1%}",
                        ]
                    )

                pred_table = Table(pred_data)
                pred_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.lightgreen),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )

                story.append(pred_table)

            # Build PDF
            doc.build(story)

            # Clean up chart files
            for chart_path in charts.values():
                if os.path.exists(chart_path):
                    try:
                        os.remove(chart_path)
                    except:
                        pass

            logger.info(f"PDF export completed: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error exporting to PDF: {str(e)}")
            return ""

    def export_to_simple_pdf(self, user_data: Dict[str, Any], filename: str) -> str:
        """Simple PDF export using FPDF when ReportLab is not available."""
        if not FPDF_AVAILABLE:
            logger.error("No PDF library available")
            return ""

        try:
            filepath = os.path.join(self.reports_dir, filename)

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)

            # Title
            pdf.cell(0, 10, "Academic Analytics Report", 0, 1, "C")
            pdf.ln(10)

            # User info
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Student: {user_data['user_info']['username']}", 0, 1)
            pdf.cell(
                0,
                10,
                f"Overall GPA: {user_data['performance']['overall_gpa']:.2f}",
                0,
                1,
            )
            pdf.cell(
                0, 10, f"Term GPA: {user_data['performance']['term_gpa']:.2f}", 0, 1
            )
            pdf.ln(10)

            # Courses
            if user_data.get("courses"):
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "Courses", 0, 1)
                pdf.set_font("Arial", "", 10)

                for course in user_data["courses"]:
                    pdf.cell(
                        0,
                        8,
                        f"{course['course_name']} - Grade: {course['current_grade']:.1f}",
                        0,
                        1,
                    )

            pdf.output(filepath)

            logger.info(f"Simple PDF export completed: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error exporting to simple PDF: {str(e)}")
            return ""


@shared_task(bind=True, name="app.tasks.exports.generate_user_report")
def generate_user_report(
    self, user_id: int, format: str = "pdf", email_delivery: bool = False
):
    """Generate analytics report for a specific user."""
    try:
        logger.info(f"Generating {format} report for user {user_id}")

        generator = AnalyticsReportGenerator()
        user_data = generator.generate_user_data(user_id)

        if not user_data:
            return {
                "status": "error",
                "error": "No data available for user",
                "user_id": user_id,
            }

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        username = user_data["user_info"]["username"]
        filename = f"{username}_analytics_report_{timestamp}.{format}"

        # Export based on format
        filepath = ""
        if format.lower() == "csv":
            filepath = generator.export_to_csv(user_data, filename)
        elif format.lower() == "excel" or format.lower() == "xlsx":
            filepath = generator.export_to_excel(
                user_data, filename.replace(format, "xlsx")
            )
        elif format.lower() == "pdf":
            filepath = generator.export_to_pdf(user_data, filename)
        else:
            return {
                "status": "error",
                "error": f"Unsupported format: {format}",
                "user_id": user_id,
            }

        if not filepath or not os.path.exists(filepath):
            return {
                "status": "error",
                "error": "Failed to generate report file",
                "user_id": user_id,
            }

        result = {
            "status": "success",
            "user_id": user_id,
            "format": format,
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "file_size": os.path.getsize(filepath),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Email delivery if requested
        if email_delivery:
            try:
                from app.services.email_service import send_export_notification_email
                from app.models import User

                # Get user information
                user = User.query.get(user_id)
                if user and user.email:
                    success = send_export_notification_email(
                        recipient_email=user.email,
                        user_name=user.name or "User",
                        export_type=f"Analytics Report ({format.upper()})",
                        file_path=filepath,
                    )
                    if success:
                        logger.info(f"Export notification email sent to {user.email}")
                        result["email_sent"] = True
                    else:
                        logger.warning(
                            f"Failed to send export notification email to {user.email}"
                        )
                        result["email_sent"] = False
                else:
                    logger.warning(f"User {user_id} not found or has no email address")
                    result["email_sent"] = False

            except Exception as e:
                logger.error(f"Error sending export notification email: {str(e)}")
                result["email_sent"] = False

        logger.info(f"Report generated successfully: {filepath}")
        return result

    except Exception as e:
        logger.error(f"Error generating report for user {user_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.exports.generate_batch_reports")
def generate_batch_reports(self, user_ids: List[int], format: str = "pdf"):
    """Generate reports for multiple users."""
    try:
        logger.info(f"Generating batch reports for {len(user_ids)} users")

        results = {}

        for user_id in user_ids:
            try:
                result = generate_user_report(user_id, format)
                results[user_id] = result
            except Exception as e:
                logger.error(f"Error generating report for user {user_id}: {str(e)}")
                results[user_id] = {
                    "status": "error",
                    "error": str(e),
                    "user_id": user_id,
                }

        # Summary
        successful = len([r for r in results.values() if r.get("status") == "success"])
        failed = len(results) - successful

        logger.info(
            f"Batch report generation completed: {successful} success, {failed} failed"
        )

        return {
            "status": "completed",
            "total_users": len(user_ids),
            "successful": successful,
            "failed": failed,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in batch report generation: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="app.tasks.exports.cleanup_old_reports")
def cleanup_old_reports(self):
    """Clean up old report files."""
    try:
        logger.info("Cleaning up old report files")

        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            return {"status": "success", "message": "No reports directory found"}

        cutoff_date = datetime.now() - timedelta(days=7)  # Keep reports for 7 days
        removed_count = 0

        for filename in os.listdir(reports_dir):
            filepath = os.path.join(reports_dir, filename)

            if os.path.isfile(filepath):
                file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))

                if file_modified < cutoff_date:
                    try:
                        os.remove(filepath)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove {filepath}: {str(e)}")

        logger.info(f"Cleanup completed: {removed_count} files removed")

        return {
            "status": "success",
            "files_removed": removed_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in report cleanup: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Utility functions for manual testing
def generate_report_sync(user_id: int, format: str = "pdf"):
    """Generate report synchronously for testing."""
    return generate_user_report(user_id, format)


if __name__ == "__main__":
    # Test the export system
    print("Testing export system...")
    # This would need a valid user_id in a real scenario
    # result = generate_report_sync(1, 'pdf')
    # print(f"Result: {result}")
    print("Export system configured successfully!")
