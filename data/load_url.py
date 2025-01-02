import csv
import sqlite3

# Define database connection and cursor
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

# Define file path
urls_file_path = "urls.csv"

# Prepare SQL statement
insert_url_sql = """
    INSERT OR IGNORE INTO urls (url) VALUES (?)
"""

# Load data from URLs file
with open(urls_file_path, "r") as csvfile:
    reader = csv.reader(csvfile, delimiter=",")
    next(reader)  # Skip header row

    for row in reader:
        url = row[0]  # Assuming the URL is the first column in your CSV
        cursor.execute(insert_url_sql, (url,))

# Commit and close connection
connection.commit()
connection.close()

print("URLs successfully uploaded to the database.")
