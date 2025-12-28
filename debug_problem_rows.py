#!/usr/bin/env python3

"""Debug specific problematic rows"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.canvas_parser import parse_canvas_grades, validate_canvas_data

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
    print("Looking at specific problematic rows...")
    
    lines = raw_canvas_data.split('\n')
    
    # Look at rows 4 and 5 (the ones with "1" as name)
    print("\nRow 4 (index 4):")
    if len(lines) > 4:
        fields = lines[4].split('\t')
        for i, field in enumerate(fields):
            print(f"  Field {i}: '{field}'")
    
    print("\nRow 5 (index 5):")  
    if len(lines) > 5:
        fields = lines[5].split('\t')
        for i, field in enumerate(fields):
            print(f"  Field {i}: '{field}'")
    
    print("\nRow 21 (Free Parking):")
    if len(lines) > 21:
        fields = lines[21].split('\t')
        for i, field in enumerate(fields):
            print(f"  Field {i}: '{field}'")
    
    print("\nRow 22 (News, Questions):")
    if len(lines) > 22:
        fields = lines[22].split('\t')
        for i, field in enumerate(fields):
            print(f"  Field {i}: '{field}'")

if __name__ == "__main__":
    main()