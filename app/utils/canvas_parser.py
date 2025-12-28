"""
Reliable Canvas Grade Parser using Beautiful Soup for HTML Extraction (Debug Logging)

This module is optimized to parse assignment data copied directly from the
Canvas "grades_summary" table (id="grades_summary"). It includes extensive
logging to help trace how rows are filtered and data is extracted.

NOTE: This requires the 'beautifulsoup4' library to be installed:
      pip install beautifulsoup4
"""

import re
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
import logging
from bs4 import BeautifulSoup, Tag

# --- Logging Setup ---
# Set logger to DEBUG level to capture all the debugging information
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) 

# Configure a basic handler for output (if not configured by the Flask program)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# --- Custom Exception ---

class CanvasParserError(Exception):
    """Custom exception for Canvas parsing errors"""
    pass

# --- Core Parser Class ---

class CanvasParser:
    """
    Robust Canvas grade data parser using Beautiful Soup for HTML structure.
    """
    
    def __init__(self, year_hint: Optional[int] = None):
        """
        Initialize parser with optional year hint for date parsing
        
        Args:
            year_hint: Year to use for date parsing (defaults to current year)
        """
        self.year_hint = year_hint or datetime.now().year
        logger.debug(f"Parser initialized with year hint: {self.year_hint}")
        
    def parse(self, raw_text: str) -> pd.DataFrame:
        """
        Parse raw Canvas HTML data into structured DataFrame.
        """
        logger.info("Starting Canvas grade HTML parsing process.")
        
        try:
            # 1. Parse HTML using Beautiful Soup
            soup = BeautifulSoup(raw_text, 'html.parser')
            
            # 2. Find the target table
            grades_table = soup.find('table', id='grades_summary')
            
            if not grades_table:
                 logger.error("grades_summary table not found.")
                 raise CanvasParserError("Could not locate the grades_summary table.")

            logger.debug("grades_summary table successfully located.")

            # 3. Find all rows that have the class 'student_assignment'
            # We will filter out group/final totals inside the loop for explicit logging
            assignment_rows = grades_table.select('tbody > tr.student_assignment')
            
            rows = []
            
            logger.info(f"Found {len(assignment_rows)} potential assignment rows to process.")
            
            for index, row in enumerate(assignment_rows):
                # Explicitly check for filtering classes (group_total, final_grade)
                row_classes = row.get('class', [])
                submission_id = row.get('id', 'N/A')

                if 'group_total' in row_classes:
                    logger.debug(f"Row {index + 1} (ID: {submission_id}) skipped: Is a group_total row.")
                    continue
                
                if 'final_grade' in row_classes:
                    logger.debug(f"Row {index + 1} (ID: {submission_id}) skipped: Is the final_grade row.")
                    continue

                # Process the valid assignment row
                parsed_data = self._parse_assignment_row(row, index + 1)
                if parsed_data:
                    rows.append(parsed_data)
                
            # 4. Create and clean DataFrame
            df = self._create_dataframe(rows)
            df = self._validate_and_clean(df)
            
            logger.info(f"Parsing complete. Final number of valid assignments imported: {len(df)}")
            return df
            
        except CanvasParserError as e:
            raise e
        except Exception as e:
            logger.error(f"Canvas HTML parsing failed unexpectedly: {e}")
            raise CanvasParserError(f"Failed to parse Canvas HTML data: {e}")

    def _parse_assignment_row(self, row_tag: Tag, index: int) -> Optional[Dict[str, Any]]:
        """Extracts data fields from a single Beautiful Soup <tr> tag with debug logging."""
        
        submission_id = row_tag.get('id', 'ID_MISSING')
        logger.debug(f"--- Processing Row {index} (Submission ID: {submission_id}) ---")

        # --- 1. Assignment Name & Category ---
        title_cell = row_tag.find('th', class_='title')
        name_tag = title_cell.find('a') if title_cell else None
        
        name = name_tag.get_text(strip=True) if name_tag else ''
        if not name:
             logger.warning(f"Row {index} skipped: Missing/invalid assignment name.")
             return None

        category_div = title_cell.find('div', class_='context') if title_cell else None
        category = category_div.get_text(strip=True) if category_div else 'Assignments'

        logger.debug(f"Name extracted: '{name}' | Category: '{category}'")

        # --- 2. Due Date ---
        due_cell = row_tag.find('td', class_='due')
        raw_due_date = due_cell.get_text(strip=True) if due_cell else ''
        due_date = self._parse_date_string(raw_due_date)
        
        if not due_date:
            logger.warning(f"Date extraction failed for '{raw_due_date}'. Date set to None.")
        else:
            logger.debug(f"Due Date extracted: {due_date}")

        # --- 3. Score and Max Score ---
        score_cell = row_tag.find('td', class_='assignment_score')
        score = None
        max_score = None
        
        if score_cell:
            # A. Actual Score: Hidden original_points span (The most accurate source for the number)
            original_points_span = score_cell.find('span', class_='original_points')
            
            if original_points_span:
                raw_score = original_points_span.get_text(strip=True)
                try:
                    score = float(raw_score) if raw_score else None
                    logger.debug(f"Score found in original_points: {score}")
                except ValueError:
                    score = None
                    logger.warning(f"Could not convert original score '{raw_score}' to float.")
            else:
                 logger.debug("original_points span not found.")

            # B. Max Score: Visible text contains "/ N"
            visible_score_span = score_cell.find('span', class_='tooltip')
            
            if visible_score_span:
                visible_text = visible_score_span.get_text(strip=True)
                max_match = re.search(r'/\s*(\d+(?:\.\d+)?)', visible_text)
                
                if max_match:
                    try:
                        max_score = float(max_match.group(1))
                        logger.debug(f"Max Score extracted from visible text: {max_score}")
                    except ValueError:
                        logger.warning(f"Could not convert max score text to float.")
                else:
                    logger.debug("Max score pattern not found in visible score text.")
            else:
                logger.debug("Visible score tooltip span not found.")

        # Final check if score is None but Max Score is present (submitted but ungraded)
        if score is None and max_score is not None:
             logger.debug(f"Score is NULL but Max Score ({max_score}) exists. Assuming submitted but ungraded.")


        logger.debug("-----------------------------------------------------")
        return {
            'name': name,
            'score': score,
            'max_score': max_score,
            'category': category,
            'due_date': due_date
        }

    # --- Date Parsing Logic ---

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """Parses Canvas date format (e.g., "Sep 30 by 11:59pm") and returns full datetime string."""
        if not date_str or date_str.strip() == '':
            return None
        
        date_time_pattern = re.compile(r'(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?:by|at)\s+(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm))', re.IGNORECASE)
        match = date_time_pattern.search(date_str)
        
        if match:
            try:
                month = match.group('month').title()
                day = int(match.group('day'))
                time_str = match.group('time').lower().replace(' ', '')
                
                if ':' not in time_str:
                    time_str = time_str.replace('am', ':00am').replace('pm', ':00pm')
                    
                date_time_str = f"{month} {day} {self.year_hint} {time_str}"
                
                try:
                    dt = datetime.strptime(date_time_str, "%b %d %Y %I:%M%p")
                except ValueError:
                    dt = datetime.strptime(date_time_str.replace(':00', ''), "%b %d %Y %I%p")
                    
                # Return full datetime string instead of just date
                return dt.strftime("%Y-%m-%d %H:%M:%S")
                
            except Exception:
                return None
        
        return None

    # --- Final Processing and Cleanup ---

    def _create_dataframe(self, rows: List[Dict[str, Any]]) -> pd.DataFrame:
        """Creates and formats the final DataFrame."""
        return pd.DataFrame(rows, columns=[
            'name', 'score', 'max_score', 'category', 'due_date'
        ])

    def _validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Final cleanup and type conversion."""
        if len(df) == 0:
            return df
        
        logger.debug("Starting final DataFrame cleaning...")
        
        # 1. Filter out junk/system assignments
        junk_keywords = ['free parking', 'news, questions, and answers', 'total']
        initial_count = len(df)
        
        df = df[~df['name'].str.contains('|'.join(junk_keywords), case=False, na=False)].copy()
        
        if len(df) < initial_count:
             logger.debug(f"Filtered out {initial_count - len(df)} non-assignment rows (e.g., Free Parking/News).")

        # 2. Clean up names by removing [time] tags
        df['name'] = df['name'].str.replace(r'\s*\[.*?min\]', '', regex=True).str.strip()
        
        # 3. Ensure correct types
        df['score'] = pd.to_numeric(df['score'], errors='coerce')
        df['max_score'] = pd.to_numeric(df['max_score'], errors='coerce')
        
        logger.debug(f"Final valid row count after cleanup: {len(df)}")

        return df.reset_index(drop=True)

# --- Entry Point Functions (for external use/compatibility) ---

def parse_canvas_grades(raw_text: str, year_hint: Optional[int] = None, **kwargs) -> pd.DataFrame:
    """
    Main entry point for parsing Canvas grades - uses HTML parsing logic.
    """
    parser = CanvasParser(year_hint=year_hint)
    return parser.parse(raw_text)

def validate_canvas_data(df: pd.DataFrame) -> Dict[str, Any]:
    # Placeholder for the validation function for completeness, same as before
    issues = []
    missing_due_dates = []
    missing_max_scores = []
    
    for i, (idx, row) in enumerate(df.iterrows()):
        name = str(row.get('name', '')).strip()
        max_score = row.get('max_score')
        due_date = row.get('due_date')
        score = row.get('score')
        
        if pd.notna(score) and (pd.isna(max_score) or max_score == 0):
             if not (score == 0 and max_score == 0) and not (score > 0 and max_score == 0):
                missing_max_scores.append(i)
                issues.append(f"Row {i + 1} ('{name}'): Missing max score (and is not clear extra credit).")
        
        # Due dates are now optional - no longer treated as missing data
        # if pd.isna(due_date) or str(due_date).strip() == '':
        #     missing_due_dates.append(i)
        #     issues.append(f"Row {i + 1} ('{name}'): Missing due date.")
    
    is_complete = (
        len(missing_max_scores) == 0
        # Due dates are now optional, so we don't require them for completion
    )
    
    return {
        'is_complete': is_complete,
        'missing_due_dates': missing_due_dates,
        'missing_max_scores': missing_max_scores,
        'issues': issues,
        'total_assignments': len(df),
    }
