#!/usr/bin/env python3

"""Debug script for Canvas import issue - standalone"""

import sys
import os
import re
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

# Simple canvas parser
class CanvasParser:
    SCORE_SLASH_RE = re.compile(r'(-|\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)')
    SCORE_PERCENT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
    
    DUE_DATE_PATTERNS = [
        re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+by\s+(\d{1,2}:?\d{0,2}\s*(?:am|pm))', re.IGNORECASE),
        re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+at\s+(\d{1,2}:?\d{0,2}\s*(?:am|pm))', re.IGNORECASE),
    ]
    
    def __init__(self, year_hint: Optional[int] = None):
        self.year_hint = year_hint or datetime.now().year
        
    def parse(self, raw_text: str) -> pd.DataFrame:
        cleaned_text = self._clean_input(raw_text)
        
        if self._is_tab_separated(cleaned_text):
            rows = self._parse_tab_separated(cleaned_text)
        else:
            rows = self._parse_unstructured(cleaned_text)
            
        df = self._create_dataframe(rows)
        df = self._validate_and_clean(df)
        
        return df
    
    def _clean_input(self, text: str) -> str:
        text = text.replace('\ufeff', '').replace('\r\n', '\n').replace('\r', '\n')
        lines = [line.rstrip() for line in text.split('\n')]
        return '\n'.join(lines)
    
    def _is_tab_separated(self, text: str) -> bool:
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return False
            
        first_line_tabs = lines[0].count('\t')
        if first_line_tabs < 3:
            return False
            
        for i, line in enumerate(lines[1:4]):
            if i >= len(lines) - 1:
                break
            if line.strip() and abs(line.count('\t') - first_line_tabs) > 2:
                return False
                
        return True
    
    def _parse_tab_separated(self, text: str) -> List[Dict[str, Any]]:
        lines = text.strip().split('\n')
        if not lines:
            return []
            
        header_line = lines[0] if lines else ''
        data_lines = lines[1:] if len(lines) > 1 else []
        
        parsed_rows = []
        
        for line in data_lines:
            if not line.strip():
                continue
                
            fields = line.split('\t')
            
            # In your Canvas format:
            # Column 0: Assignment name
            # Column 1: Category  
            # Column 2: Due date (like "Oct 1 by 11:59pm")
            # Column 6: Score info (like "5 / 5" or "- / 10")
            
            if len(fields) < 2:
                continue
                
            assignment_name = fields[0].strip()
            if not assignment_name:
                continue
                
            category = fields[1].strip() if len(fields) > 1 else 'Assignments'
            
            due_date = None
            if len(fields) > 2 and fields[2].strip():
                due_date = self._parse_due_date(fields[2].strip())
            
            score = None
            max_score = None
            
            # Look for score information in fields
            for i, field in enumerate(fields):
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
    
    def _parse_unstructured(self, text: str) -> List[Dict[str, Any]]:
        # Your fallback logic here
        return []
    
    def _parse_due_date(self, date_str: str) -> Optional[str]:
        if not date_str or date_str.strip() == '':
            return None
            
        date_str = date_str.strip()
        
        for pattern in self.DUE_DATE_PATTERNS:
            match = pattern.search(date_str)
            if match:
                try:
                    month = match.group(1).title()
                    day = int(match.group(2))
                    time_str = match.group(3).lower().replace(' ', '')
                    
                    if ':' not in time_str:
                        time_str = time_str.replace('am', ':00am').replace('pm', ':00pm')
                    
                    date_time_str = f"{month} {day} {self.year_hint} {time_str}"
                    dt = datetime.strptime(date_time_str, "%b %d %Y %I:%M%p")
                    return dt.strftime("%Y-%m-%d")
                    
                except Exception as e:
                    print(f"Failed to parse date '{date_str}': {e}")
                    continue
        
        return None
    
    def _parse_score(self, score_str: str) -> Tuple[Optional[float], Optional[float]]:
        if not score_str or score_str.strip() == '':
            return None, None
            
        score_str = score_str.strip()
        
        if 'file upload submission' in score_str.lower():
            match = self.SCORE_SLASH_RE.search(score_str)
            if match:
                try:
                    max_score = float(match.group(2))
                    return None, max_score
                except ValueError:
                    pass
        
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
        
        match = self.SCORE_PERCENT_RE.search(score_str)
        if match:
            try:
                percent = float(match.group(1))
                return percent, 100.0
            except ValueError:
                pass
        
        return None, None
    
    def _create_dataframe(self, rows: List[Dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame({
                'name': pd.Series(dtype='str'),
                'score': pd.Series(dtype='float64'),
                'max_score': pd.Series(dtype='float64'),
                'category': pd.Series(dtype='str'),
                'due_date': pd.Series(dtype='str')
            })
        
        return pd.DataFrame(rows)
    
    def _validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) == 0:
            return df
        
        df = df.dropna(subset=['name'])
        valid_name_mask = df['name'].astype(str).str.strip() != ''
        df = df[valid_name_mask]
        
        if len(df) == 0:
            empty_df = pd.DataFrame({
                'name': pd.Series(dtype='str'),
                'score': pd.Series(dtype='float64'), 
                'max_score': pd.Series(dtype='float64'),
                'category': pd.Series(dtype='str'),
                'due_date': pd.Series(dtype='str')
            })
            return empty_df
        
        df['name'] = df['name'].str.strip()
        df['category'] = df['category'].fillna('Assignments')
        empty_category_mask = df['category'].astype(str).str.strip() == ''
        df.loc[empty_category_mask, 'category'] = 'Assignments'
        
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
        df['max_score'] = pd.to_numeric(df['max_score'], errors='coerce')
        
        return df.reset_index(drop=True)

# Your raw Canvas data
raw_canvas_data = """Name	Due	Submitted	Status	Score		Details	Submission Progress Status
Have a look around (due week 1) [20min]	Assignments	Sep 30 by 11:59pm	Sep 30 at 9:48pm		Click to test a different score	5 / 5   
Discover "News/Q&A" (due week 1) [20min]	Contributions	Oct 1 by 11:59pm			Click to test a different score	- / 10 
Practice submitting assignments, including screenshots (due week 1) [10min]	Assignments	Oct 2 by 11:59pm	Sep 30 at 10:07pm		Click to test a different score	5 / 5    
1	Discussion: Welcome to IS301! —SUBSCRIBE for updates [20min]	Assignments	Oct 5 by 11:59pm	Sep 30 at 10:24pm		Click to test a different score	5 / 5    
1	Skills assessment—where are you now? (There are no wrong answers!) [10min]	Self Assessments	Oct 5 by 11:59pm	Sep 30 at 10:12pm		Click to test a different score	1 / 1   
Week 1 assessment—what have you learned? [10min]	Self Assessments	Oct 7 by 11:59pm	Oct 6 at 1:26pm		Click to test a different score	1 / 1   
Quiz W2: Containers	Quizzes and Exams	Oct 12 by 11:59pm	Oct 8 at 3:10pm		Click to test a different score	2.76 / 3   
Week 2 assessment—what have you learned?	Self Assessments	Oct 12 by 11:59pm	Oct 8 at 4:08pm		Click to test a different score	1 / 1   
BYO reference sheet for OCI image/container solutions, including examples and references [30min]	Assignments	Oct 14 by 11:59pm			Click to test a different score	- / 10 
Interact with a container running on your system [40min]	Assignments	Oct 14 by 11:59pm	Oct 7 at 3:17pm		Click to test a different score	File Upload Submission / 10 
Set up DockerHub account and Docker Desktop [20-40min]	Assignments	Oct 14 by 11:59pm	Oct 6 at 11:20pm		Click to test a different score	10 / 10   
Quiz W3: AWS	Quizzes and Exams	Oct 19 by 11:59pm			Click to test a different score	- / 3 
Week 3 assessment—what have you learned?	Self Assessments	Oct 19 by 11:59pm			Click to test a different score	- / 1 
Provision and connect to a Linux system [5-30min]	Assignments	Oct 21 by 11:59pm			Click to test a different score	- / 10 
Install a LAMP public web server on an Ubuntu system...and keep it running until grading completed [10-60min]	Assignments	Oct 23 by 11:59pm			Click to test a different score	- / 10 
Week 4 assessment—what have you learned?	Self Assessments	Oct 26 by 11:59pm			Click to test a different score	- / 1 
Quiz W4: Git	Quizzes and Exams	Oct 26 by 11:59pm			Click to test a different score	- / 3 
Set up a remote Git repository [30-60min]	Assignments	Oct 28 by 11:59pm			Click to test a different score	- / 10 
Automate data normalization—part 1: candidate sources [40min]	Assignments	Oct 30 by 11:59pm			Click to test a different score	- / 10 
BYO reference sheet for version control with git, including examples and references (with EXTRA CREDIT opportunity) [30min]	Assignments	Oct 30 by 11:59pm			Click to test a different score	- / 10 
Free Parking—keep stuff handy	Assignments				Click to test a different score	- 
News, Questions, and Answers—SUBSCRIBE for updates	Assignments	Sep 30 at 9:55pm		Click to test a different score	1 / 0"""

def main():
    print("Debugging Canvas import issue...")
    print(f"Raw data length: {len(raw_canvas_data)} characters")
    print(f"Number of lines: {len(raw_canvas_data.split('\n'))}")
    print(f"Tab count in first line: {raw_canvas_data.split('\n')[0].count('\t')}")
    
    # Show first few lines parsed
    lines = raw_canvas_data.split('\n')
    print("\nFirst 3 lines:")
    for i, line in enumerate(lines[:3]):
        fields = line.split('\t')
        print(f"Line {i}: {len(fields)} fields")
        for j, field in enumerate(fields):
            print(f"  Field {j}: '{field}'")
    
    # Try parsing
    try:
        parser = CanvasParser(year_hint=2024)
        df = parser.parse(raw_canvas_data)
        print(f"\nParsed {len(df)} assignments:")
        
        for i, row in df.iterrows():
            print(f"{i}: Name='{row['name']}', Score={row['score']}, Max={row['max_score']}, Due='{row['due_date']}', Category='{row['category']}'")
        
        print(f"\nIssues analysis:")
        missing_due_dates = 0
        missing_max_scores = 0
        for i, row in df.iterrows():
            if pd.isna(row['due_date']) or row['due_date'] is None or str(row['due_date']).strip() == '':
                missing_due_dates += 1
                print(f"  Row {i+1}: Missing due date for '{row['name']}'")
            if pd.isna(row['max_score']) or row['max_score'] is None:
                missing_max_scores += 1
                print(f"  Row {i+1}: Missing max score for '{row['name']}'")
        
        print(f"\nSummary: {missing_due_dates} missing due dates, {missing_max_scores} missing max scores")
            
    except Exception as e:
        print(f"Error parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()