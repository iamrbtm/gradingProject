import csv
import json
from typing import List, Dict, Any, Tuple
from app.models import Assignment, GradeCategory, db
from datetime import datetime

class AssignmentImporter:
    """
    Import assignments from a CSV or JSON file and insert them into the database.
    """
    REQUIRED_FIELDS = ["name", "max_score", "due_date"]

    def import_assignments(self, file_path: str, course_id: int) -> Dict[str, Any]:
        """
        Import assignments from a CSV or JSON file.
        Args:
            file_path (str): Path to the file to import.
            course_id (int): The course ID to associate assignments with.
        Returns:
            dict: Summary of import results (successes, errors).
        """
        file_type = self.detect_file_type(file_path)
        if file_type == "csv":
            assignments, errors = self.parse_csv(file_path)
        elif file_type == "json":
            assignments, errors = self.parse_json(file_path)
        else:
            return {"success": False, "errors": ["Unsupported file type."]}

        valid_assignments, validation_errors = self.validate_assignments(assignments)
        errors.extend(validation_errors)
        inserted, db_errors = self.insert_assignments(valid_assignments, course_id)
        errors.extend(db_errors)
        return {"success": len(inserted) > 0, "inserted": inserted, "errors": errors}

    def detect_file_type(self, file_path: str) -> str:
        """Detect file type by extension or by content sniffing.
        Falls back to content-based detection when the path has no extension
        (e.g., temp files from uploads).
        """
        lower = file_path.lower()
        if lower.endswith('.csv'):
            return 'csv'
        if lower.endswith('.json'):
            return 'json'
        # Content-based sniffing
        try:
            # Try JSON first
            with open(file_path, encoding='utf-8') as f:
                json.load(f)
                return 'json'
        except Exception:
            pass
        try:
            # Try CSV by reading a small sample and using Sniffer
            with open(file_path, newline='', encoding='utf-8') as f:
                sample = f.read(2048)
                if not sample.strip():
                    return 'unknown'
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    # If it has headers, DictReader will work downstream
                    return 'csv'
                except Exception:
                    # Heuristic: look for common delimiters and header names
                    if ',' in sample or '\t' in sample or ';' in sample:
                        return 'csv'
        except Exception:
            pass
        return 'unknown'

    def parse_csv(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        assignments = []
        errors = []
        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    assignments.append(dict(row))
        except Exception as e:
            errors.append(f"CSV parse error: {e}")
        return assignments, errors

    def parse_json(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        assignments = []
        errors = []
        try:
            with open(file_path, encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                if isinstance(data, list):
                    assignments = data
                else:
                    errors.append("JSON root must be a list of assignments.")
        except Exception as e:
            errors.append(f"JSON parse error: {e}")
        return assignments, errors

    def validate_assignments(self, assignments: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        valid = []
        errors = []
        for idx, a in enumerate(assignments):
            missing = [f for f in self.REQUIRED_FIELDS if f not in a or not a[f]]
            if missing:
                errors.append(f"Assignment {idx+1} missing fields: {', '.join(missing)}")
                continue
            # Validate types
            try:
                a["max_score"] = float(a["max_score"])
                if "score" in a and a["score"]:
                    a["score"] = float(a["score"])
                else:
                    a["score"] = None
                if a["due_date"]:
                    # Handle both string formats
                    due_date_str = a["due_date"]
                    if isinstance(due_date_str, str):
                        # Remove microseconds if present
                        if '.' in due_date_str:
                            due_date_str = due_date_str.split('.')[0]
                        a["due_date"] = datetime.fromisoformat(due_date_str)
                    else:
                        a["due_date"] = due_date_str
                else:
                    a["due_date"] = None
            except Exception as e:
                errors.append(f"Assignment {idx+1} type error: {e}")
                continue
            valid.append(a)
        return valid, errors

    def find_or_create_category(self, category_name: str, course_id: int):
        """Find existing category or create a new one."""
        if not category_name:
            return None
        
        category = GradeCategory.query.filter_by(name=category_name, course_id=course_id).first()
        if not category:
            # Create new category with default weight
            category = GradeCategory(name=category_name, weight=0.0, course_id=course_id)
            db.session.add(category)
            db.session.commit()
        return category.id

    def insert_assignments(self, assignments: List[Dict[str, Any]], course_id: int) -> Tuple[List[str], List[str]]:
        inserted = []
        errors = []
        for a in assignments:
            try:
                # Handle category field
                category_id = None
                if "category" in a and a["category"]:
                    category_id = self.find_or_create_category(a["category"], course_id)
                elif "category_id" in a:
                    category_id = a["category_id"]

                assignment = Assignment(
                    name=a["name"],
                    score=a["score"],
                    max_score=a["max_score"],
                    course_id=course_id,
                    due_date=a["due_date"],
                    category_id=category_id
                )
                db.session.add(assignment)
                db.session.commit()
                inserted.append(a["name"])
            except Exception as e:
                db.session.rollback()
                errors.append(f"DB error for '{a.get('name', 'unknown')}': {e}")
        return inserted, errors
