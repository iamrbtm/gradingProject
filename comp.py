import mysql.connector
import xml.etree.ElementTree as ET
import os

# Load sensitive credentials from environment variables
db_user = 'rbtm2006'
db_password = 'Braces4me##'
db_host = 'localhost'
db_name = 'Vendor_Booth_RESERVATION_Scheduling'

# Parse the XML file
try:
    tree = ET.parse('Vendor_Booth_RESERVATION_Scheduling_P4_1_1st__custom.xml')
    root = tree.getroot()
except ET.ParseError as e:
    print(f"Error parsing XML file: {e}")
    exit(1)
except FileNotFoundError:
    print("XML file not found.")
    exit(1)

# Connect to MySQL and process data
try:
    conn = mysql.connector.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        database=db_name
    )
    cursor = conn.cursor()

    # Build a set of IDs present in the XML for fast lookup
    xml_ids = {item.find('id').text for item in root.findall('Vendor') if item.find('id') is not None}

    # Query all IDs from the database and check presence in the XML
    cursor.execute("SELECT id FROM Vendor")
    for (db_id,) in cursor:
        if db_id in xml_ids:
            print(f"ID {db_id} is in Database and XML")
        else:
            print(f"ID {db_id} is in Database but MISSING from XML")
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
