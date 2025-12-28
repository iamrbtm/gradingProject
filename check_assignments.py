import pymysql
import os

# Database connection
db_config = {
    'host': 'jeremyguill.com',
    'user': 'onlymyli',
    'password': 'Braces4me##',
    'database': 'onlymyli_grades',
    'port': 3306
}

try:
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    # Query assignments for course_id=2
    query = """
    SELECT a.id, a.name, a.score, a.max_score, a.due_date, a.completed, gc.name as category_name
    FROM assignment a
    LEFT JOIN grade_category gc ON a.category_id = gc.id
    WHERE a.course_id = 2
    ORDER BY a.id
    """
    cursor.execute(query)
    results = cursor.fetchall()

    print("Assignments for course_id=2:")
    print("ID | Name | Score | Max Score | Due Date | Completed | Category")
    print("-" * 80)
    for row in results:
        id, name, score, max_score, due_date, completed, category = row
        print(f"{id} | {name} | {score} | {max_score} | {due_date} | {completed} | {category}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")