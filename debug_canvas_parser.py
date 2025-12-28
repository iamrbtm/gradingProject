#!/usr/bin/env python3

"""
Test script to debug Canvas parsing issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.canvas_parser import parse_canvas_grades
import pandas as pd

# Sample Canvas data
canvas_data = """Name	Due	Submitted	Status	Score		Details	Submission Progress StatusSyllabus QuizQuizzesOct 2, 2024 by 11:59pm	Sep 26, 2024 at 10:21pm		Click to test a different score15 / 15  Quiz 1 - zyBooks Chapters 2 through 5QuizzesOct 22, 2024 by 11:59pm	Oct 10, 2024 at 9:44pm		Click to test a different score37 / 38  zyBooks Chapters 2 through 5 ChallengeszyBooks Chapters 2-12 ChallengesOct 22, 2024 by 11:59pm	Oct 1, 2024 at 10:28pm		Click to test a different score100 / 100  zyBooks Chapters 2 through 5 LabszyBooks Chapters 2-12 LabsOct 22, 2024 by 11:59pm	Oct 10, 2024 at 9:23pm		Click to test a different score100 / 100  zyBooks Chapters 2 through 5 ParticipationzyBooks Chapters 2-12 ParticipationOct 22, 2024 by 11:59pm	Sep 29, 2024 at 10:50pm		Click to test a different score100 / 100  zyBooks Chapter 6 ChallengezyBooks Chapters 2-12 ChallengesOct 29, 2024 by 11:59pm	Oct 13, 2024 at 9:49pm		Click to test a different score100 / 100  zyBooks Chapter 6 LabszyBooks Chapters 2-12 LabsOct 29, 2024 by 11:59pm	Oct 16, 2024 at 11:47pm		Click to test a different score100 / 100  zyBooks Chapter 6 ParticipationzyBooks Chapters 2-12 ParticipationOct 29, 2024 by 11:59pm	Oct 13, 2024 at 9:44pm		Click to test a different score100 / 100  Quiz 2 - zyBooks Chapters 6 & 7QuizzesNov 5, 2024 by 11:59pm	Oct 19, 2024 at 12:48am		Click to test a different score41 / 45  zyBooks Chapter 7 ChallengezyBooks Chapters 2-12 ChallengesNov 5, 2024 by 11:59pm	Oct 18, 2024 at 11:20pm		Click to test a different score100 / 100  zyBooks Chapter 7 LabszyBooks Chapters 2-12 LabsNov 5, 2024 by 11:59pm	Oct 19, 2024 at 12:05am		Click to test a different score100 / 100  zyBooks Chapter 7 ParticipationzyBooks Chapters 2-12 ParticipationNov 5, 2024 by 11:59pm	Oct 18, 2024 at 9:18pm		Click to test a different score100 / 100  zyBooks Chapter 8 ChallengezyBooks Chapters 2-12 ChallengesNov 12, 2024 by 11:59pm	Oct 19, 2024 at 1:09am		Click to test a different score100 / 100  zyBooks Chapter 8 LabszyBooks Chapters 2-12 LabsNov 12, 2024 by 11:59pm	Oct 22, 2024 at 10:57pm		Click to test a different score100 / 100  zyBooks Chapter 8 ParticipationzyBooks Chapters 2-12 ParticipationNov 12, 2024 by 11:59pm	Oct 19, 2024 at 1:02am		Click to test a different score100 / 100  Quiz 3 - zyBooks Chapters 8 & 9QuizzesNov 19, 2024 by 11:59pm	Nov 13, 2024 at 10:32pm		Click to test a different score45 / 50   zyBooks Chapter 9 ChallengezyBooks Chapters 2-12 ChallengesNov 19, 2024 by 11:59pm	Oct 24, 2024 at 9:48pm		Click to test a different score100 / 100   zyBooks Chapter 9 LabszyBooks Chapters 2-12 LabsNov 19, 2024 by 11:59pm	Nov 12, 2024 at 12:29pm		Click to test a different score100 / 100   zyBooks Chapter 9 ParticipationzyBooks Chapters 2-12 ParticipationNov 19, 2024 by 11:59pm	Nov 13, 2024 at 9:41pm		Click to test a different score100 / 100   zyBooks Chapter 10 ChallengezyBooks Chapters 2-12 ChallengesNov 26, 2024 by 11:59pm	Nov 17, 2024 at 8:30pm		Click to test a different score100 / 100   zyBooks Chapter 10 LabszyBooks Chapters 2-12 LabsNov 26, 2024 by 11:59pm	Nov 19, 2024 at 1:56pm		Click to test a different score100 / 100   zyBooks Chapter 10 ParticipationzyBooks Chapters 2-12 ParticipationNov 26, 2024 by 11:59pm	Nov 19, 2024 at 1:58pm		Click to test a different score100 / 100   Quiz 4 - zyBooks Chapters 10 & 11QuizzesDec 3, 2024 by 11:59pm	Nov 26, 2024 at 11:47pm		Click to test a different score45 / 50   zyBooks Chapter 11 ChallengezyBooks Chapters 2-12 ChallengesDec 3, 2024 by 11:59pm	Nov 25, 2024 at 10:32pm		Click to test a different score100 / 100   zyBooks Chapter 11 LabszyBooks Chapters 2-12 LabsDec 3, 2024 by 11:59pm	Nov 26, 2024 at 1:30am		Click to test a different score100 / 100   zyBooks Chapter 11 ParticipationzyBooks Chapters 2-12 ParticipationDec 3, 2024 by 11:59pm	Nov 25, 2024 at 10:27pm		Click to test a different score100 / 100   zyBooks Chapter 12 ChallengezyBooks Chapters 2-12 ChallengesDec 10, 2024 by 11:59pm	Nov 26, 2024 at 1:19pm		Click to test a different score100 / 100   zyBooks Chapter 12 LabszyBooks Chapters 2-12 LabsDec 10, 2024 by 11:59pm	Nov 26, 2024 at 7:34pm		Click to test a different score100 / 100   zyBooks Chapter 12 ParticipationzyBooks Chapters 2-12 ParticipationDec 10, 2024 by 11:59pm	Nov 26, 2024 at 1:15pm		Click to test a different score100 / 100"""

def main():
    print("Testing Canvas parser...")
    df = parse_canvas_grades(canvas_data)
    
    print(f"\nParsed {len(df)} assignments:")
    print("=" * 80)
    
    for idx, row in df.iterrows():
        print(f"{idx}: {row['name']}")
        print(f"    Score: {row['score']} / {row['max_score']}")
        print(f"    Category: {row['category']}")
        print(f"    Due: {row['due_date']}")
        print()
    
    # Expected results for comparison
    expected = [
        ("Syllabus Quiz", 15, 15, "2024-10-02"),
        ("Quiz 1 - zyBooks Chapters 2 through 5", 37, 38, "2024-10-22"),
        ("zyBooks Chapters 2 through 5 Challenges", 100, 100, "2024-10-22"),
        ("zyBooks Chapters 2 through 5 Labs", 100, 100, "2024-10-22"),
        ("zyBooks Chapters 2 through 5 Participation", 100, 100, "2024-10-22"),
        ("Quiz 2 - zyBooks Chapters 6 & 7", 41, 45, "2024-11-05"),
        ("Quiz 3 - zyBooks Chapters 8 & 9", 45, 50, "2024-11-19"),
        ("Quiz 4 - zyBooks Chapters 10 & 11", 45, 50, "2024-12-03"),
    ]
    
    print("\nExpected key assignments:")
    print("=" * 80)
    for name, score, max_score, due_date in expected:
        print(f"{name}: {score}/{max_score} due {due_date}")

if __name__ == "__main__":
    main()