from typing import Optional, Tuple, List
from datetime import datetime
from app.models import Assignment, GradeCategory, Course, Term


class GradeCalculatorService:
    """Service class for grade calculation business logic."""
    
    @staticmethod
    def calculate_assignment_percentage(assignment: Assignment) -> Tuple[Optional[float], bool]:
        """Calculate assignment percentage and whether it's graded."""
        if assignment.score is None:
            return None, False
        
        # Handle extra credit assignments (max_score = 0)
        if assignment.max_score == 0:
            if hasattr(assignment, 'is_extra_credit') and assignment.is_extra_credit:
                # Extra credit: return score as bonus points (not percentage)
                return float(assignment.score), True
            else:
                return None, False
        
        return (float(assignment.score) / float(assignment.max_score)) * 100, True
    
    @staticmethod
    def calculate_category_average(grade_category: GradeCategory, assignments: List[Assignment]) -> Tuple[Optional[float], bool]:
        """Calculate category average percentage and whether it's active."""
        total_earned_points = 0.0
        total_possible_points = 0.0
        
        category_assignments = [a for a in assignments if a.category_id == grade_category.id]
        
        for assignment in category_assignments:
            percentage, is_graded = GradeCalculatorService.calculate_assignment_percentage(assignment)
            if is_graded and assignment.score is not None and assignment.max_score is not None:
                total_earned_points += float(assignment.score)
                total_possible_points += float(assignment.max_score)
        
        if total_possible_points > 0.0:
            average_percentage = (total_earned_points / total_possible_points) * 100
            return average_percentage, True
        else:
            return None, False
    
    @staticmethod
    def calculate_course_grade(course: Course) -> float:
        """Calculate overall course grade percentage."""
        if course.is_weighted:
            return GradeCalculatorService._calculate_weighted_grade(course)
        else:
            return GradeCalculatorService._calculate_unweighted_grade(course)
    
    @staticmethod
    def _calculate_weighted_grade(course: Course) -> float:
        """Calculate weighted course grade."""
        weighted_sum = 0.0
        total_active_weight = 0.0
        
        for category in course.grade_categories:
            average_percentage, is_active = GradeCalculatorService.calculate_category_average(
                category, course.assignments
            )
            if is_active and average_percentage is not None:
                category_decimal_average = average_percentage / 100
                weighted_sum += (category_decimal_average * category.weight)
                total_active_weight += category.weight
        
        if total_active_weight > 0.0:
            return (weighted_sum / total_active_weight) * 100
        else:
            return 0.0
    
    @staticmethod
    def _calculate_unweighted_grade(course: Course) -> float:
        """Calculate unweighted course grade."""
        graded_assignments = [a for a in course.assignments if a.score is not None]
        
        if graded_assignments:
            total_score = sum(float(a.score) for a in graded_assignments if a.score is not None)
            total_max_score = sum(float(a.max_score) for a in graded_assignments if a.max_score is not None)
            return (total_score / total_max_score) * 100 if total_max_score > 0 else 0.0
        else:
            return 0.0
    
    @staticmethod
    def convert_percentage_to_gpa_scale(percentage: Optional[float]) -> Optional[float]:
        """Convert percentage grade to 4.0 GPA scale."""
        if percentage is None:
            return None
        if percentage >= 90:
            return 4.0
        elif percentage >= 80:
            return 3.0
        elif percentage >= 70:
            return 2.0
        elif percentage >= 60:
            return 1.0
        else:
            return 0.0
    
    @staticmethod
    def calculate_gpa_contribution(course: Course, course_grade_percentage: Optional[float]) -> Optional[float]:
        """Calculate GPA contribution for a course."""
        if course_grade_percentage is None:
            return None
        gpa_value = GradeCalculatorService.convert_percentage_to_gpa_scale(course_grade_percentage)
        return gpa_value * float(course.credits) if gpa_value is not None else None
    
    @staticmethod
    def calculate_term_gpa(term: Term) -> float:
        """Calculate overall GPA for a term."""
        total_quality_points = 0.0
        total_credits_attempted = 0.0
        
        for course in term.courses:
            course_grade_percentage = GradeCalculatorService.calculate_course_grade(course)
            if course_grade_percentage is not None:
                gpa_points = GradeCalculatorService.convert_percentage_to_gpa_scale(course_grade_percentage)
                if gpa_points is not None:
                    total_quality_points += (gpa_points * float(course.credits))
                    total_credits_attempted += float(course.credits)
        
        return total_quality_points / total_credits_attempted if total_credits_attempted > 0.0 else 0.0
    
    @staticmethod
    def calculate_percentage_complete(course: Course) -> float:
        """Calculate percentage of assignments completed."""
        all_assignments = course.assignments
        if not all_assignments:
            return 0.0
        
        graded_assignments = [a for a in all_assignments if a.score is not None]
        return (len(graded_assignments) / len(all_assignments)) * 100