#!/usr/bin/env python3
"""
Simple test script to test the Canvas parser with user's actual data
"""

import sys
import os
import re
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

# Define the CanvasParser class directly in this file to avoid import issues
class CanvasParser:
    # Score patterns
    SCORE_SLASH_RE = re.compile(r'(-|\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)')
    SCORE_PERCENT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
    
    # Date patterns for Canvas format
    DUE_DATE_PATTERNS = [
        re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+by\s+(\d{1,2}:?\d{0,2}\s*(?:am|pm))', re.IGNORECASE),
        re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+at\s+(\d{1,2}:?\d{0,2}\s*(?:am|pm))', re.IGNORECASE),
    ]
    
    def __init__(self, year_hint: Optional[int] = None):
        self.year_hint = year_hint or datetime.now().year
        
    def parse(self, raw_text: str) -> pd.DataFrame:
        """Parse raw Canvas text data into structured DataFrame"""
        # Clean and normalize the input
        cleaned_text = self._clean_input(raw_text)
        
        # Parse as tab-separated (this is the format we're dealing with)
        rows = self._parse_tab_separated(cleaned_text)
            
        # Create DataFrame from parsed rows
        df = self._create_dataframe(rows)
        
        print(f"Successfully parsed {len(df)} assignments")
        return df
    
    def _create_dataframe(self, rows: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create DataFrame from parsed rows"""
        if not rows:
            return pd.DataFrame({
                'name': pd.Series(dtype='str'),
                'score': pd.Series(dtype='float64'),
                'max_score': pd.Series(dtype='float64'),
                'category': pd.Series(dtype='str'),
                'due_date': pd.Series(dtype='str')
            })
        
        return pd.DataFrame(rows)
    
    def _clean_input(self, text: str) -> str:
        """Clean and normalize input text"""
        # Remove BOM and normalize line endings
        text = text.replace('\ufeff', '').replace('\r\n', '\n').replace('\r', '\n')
        # Remove extra whitespace but preserve structure
        lines = [line.rstrip() for line in text.split('\n')]
        return '\n'.join(lines)
    
    def _parse_tab_separated(self, text: str) -> List[Dict[str, Any]]:
        """Parse tab-separated Canvas data (correct format for user's data)"""
        lines = text.strip().split('\n')
        if not lines:
            return []
            
        # Skip header line
        header_line = lines[0] if lines else ''
        data_lines = lines[1:] if len(lines) > 1 else []
        
        parsed_rows = []
        
        for line in data_lines:
            if not line.strip():
                continue
                
            fields = line.split('\t')
            
            # In user's format:
            # Column 0: Assignment name
            # Column 1: Category (like "Assignments", "Quizzes and Exams")  
            # Column 2: Due date (like "Oct 1 by 11:59pm")
            # Column 6: Score info (like "5 / 5" or "- / 10")
            
            if len(fields) < 2:
                continue
                
            # Extract assignment name
            assignment_name = fields[0].strip()
            if not assignment_name:
                continue
                
            # Extract category
            category = fields[1].strip() if len(fields) > 1 else 'Assignments'
            
            # Extract due date from column 2
            due_date = None
            if len(fields) > 2 and fields[2].strip():
                due_date = self._parse_due_date(fields[2].strip())
            
            # Extract score from column 6 (or look in other columns)
            score = None
            max_score = None
            
            # Try column 6 first (typical location)
            if len(fields) > 6 and fields[6].strip():
                score, max_score = self._parse_score(fields[6])
            
            # If not found, search other columns
            if score is None and max_score is None:
                for field in fields:
                    if field and ('/' in field or 'click to test' in field.lower()):
                        temp_score, temp_max = self._parse_score(field)
                        if temp_score is not None or temp_max is not None:
                            score, max_score = temp_score, temp_max
                            break
            
            parsed_rows.append({
                'name': assignment_name,
                'score': score,
                'max_score': max_score,
                'category': category if category else 'Assignments',
                'due_date': due_date
            })
        
        return parsed_rows
    
    def _parse_due_date(self, date_str: str) -> Optional[str]:
        """Parse due date from various Canvas formats"""
        if not date_str or date_str.strip() == '':
            return None
            
        date_str = date_str.strip()
        
        # Try each pattern
        for pattern in self.DUE_DATE_PATTERNS:
            match = pattern.search(date_str)
            if match:
                try:
                    month = match.group(1).title()
                    day = int(match.group(2))
                    time_str = match.group(3).lower().replace(' ', '')
                    
                    # Add :00 to times without minutes
                    if ':' not in time_str:
                        time_str = time_str.replace('am', ':00am').replace('pm', ':00pm')
                    
                    # Parse into datetime
                    date_time_str = f"{month} {day} {self.year_hint} {time_str}"
                    dt = datetime.strptime(date_time_str, "%b %d %Y %I:%M%p")
                    return dt.strftime("%Y-%m-%d")
                    
                except Exception as e:
                    print(f"Failed to parse date '{date_str}': {e}")
                    continue
        
        return None
    
    def _parse_score(self, score_str: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse score from various Canvas formats"""
        if not score_str or score_str.strip() == '':
            return None, None
            
        score_str = score_str.strip()
        
        # Handle special cases
        if 'file upload submission' in score_str.lower():
            # Look for max score after "/ "
            match = self.SCORE_SLASH_RE.search(score_str)
            if match:
                try:
                    max_score = float(match.group(2))
                    return None, max_score
                except ValueError:
                    pass
        
        # Try slash format "x / y"
        match = self.SCORE_SLASH_RE.search(score_str)
        if match:
            try:
                score_part = match.group(1).strip()
                max_part = match.group(2).strip()
                
                score = float(score_part) if score_part != '-' else None
                max_score = float(max_part)
                
                return score, max_score
            except ValueError:
                pass
        
        return None, None

def test_canvas_parser():
    # Read user's Canvas data
    try:
        with open('user_canvas_data.txt', 'r') as f:
            canvas_data = f.read()
    except FileNotFoundError:
        print("Error: user_canvas_data.txt not found")
        return
    
    print("Canvas Parser Test with User's Data")
    print("=" * 50)
    print(f"Input data length: {len(canvas_data)} characters")
    print()
    
    # Parse the data
    parser = CanvasParser(year_hint=2024)
    df = parser.parse(canvas_data)
    
    print("Parsed Assignments:")
    print("-" * 80)
    print(f"{'#':<3} {'Name':<50} {'Score':<12} {'Category':<15} {'Due Date'}")
    print("-" * 80)
    
    for i in range(len(df)):
        row = df.iloc[i]
        name = str(row['name'])[:47] + "..." if len(str(row['name'])) > 50 else str(row['name'])
        score = row['score']
        max_score = row['max_score']
        category = str(row['category'])
        due_date = row['due_date']
        
        score_str = f"{score}/{max_score}" if score is not None and max_score is not None else f"-/{max_score}" if max_score is not None else "No score"
        due_str = str(due_date) if due_date is not None else "No due date"
        
        print(f"{i+1:<3} {name:<50} {score_str:<12} {category:<15} {due_str}")
    
    print()
    print("Summary:")
    print("-" * 30)
    print(f"Total assignments: {len(df)}")
    
    # Count missing data
    missing_due_dates = df['due_date'].isna().sum()
    missing_max_scores = df['max_score'].isna().sum()
    
    print(f"Missing due dates: {missing_due_dates}")
    print(f"Missing max scores: {missing_max_scores}")
    
    # Calculate success rates
    due_date_success = (len(df) - missing_due_dates) / len(df) * 100 if len(df) > 0 else 0
    max_score_success = (len(df) - missing_max_scores) / len(df) * 100 if len(df) > 0 else 0
    
    print(f"Due date parsing success: {due_date_success:.1f}%")
    print(f"Max score parsing success: {max_score_success:.1f}%")

if __name__ == "__main__":
    test_canvas_parser()