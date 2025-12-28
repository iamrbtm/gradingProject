#!/usr/bin/env python3

"""
Debug Canvas text structure
"""

canvas_data = """Name	Due	Submitted	Status	Score		Details	Submission Progress StatusSyllabus QuizQuizzesOct 2, 2024 by 11:59pm	Sep 26, 2024 at 10:21pm		Click to test a different score15 / 15  Quiz 1 - zyBooks Chapters 2 through 5QuizzesOct 22, 2024 by 11:59pm	Oct 10, 2024 at 9:44pm		Click to test a different score37 / 38"""

def main():
    lines = canvas_data.splitlines()
    print("Canvas text structure analysis:")
    print("=" * 50)
    
    for i, line in enumerate(lines):
        print(f"Line {i}: '{line}'")
        print(f"  Length: {len(line)}")
        print(f"  Split by tab: {line.split(chr(9))}")  # Tab character
        print()

if __name__ == "__main__":
    main()