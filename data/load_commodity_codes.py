import csv
import sqlite3

# Database connection and cursor
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

# Commodity code file path
commodity_code_file_path = "commodity_code.csv"

# SQL statement
insert_commodity_code_sql = """
    INSERT INTO commodity_code (hs_code, description, code) VALUES (?, ?, ?)
"""

# Load data from commodity code file
with open(commodity_code_file_path, "r") as csvfile:
    reader = csv.reader(csvfile, delimiter=",")
    next(reader)  # Skip header row

    for row in reader:
        # Ensure the row has at least 3 values
        if len(row) >= 3:
            hs_code, description, code = row[:3]  # Extract hs_code, description, and code

            cursor.execute(insert_commodity_code_sql, (hs_code, description, code))
        else:
            print(f"Skipping row with insufficient values: {row}")

# Commit and close connection
connection.commit()
connection.close()

print("Commodity codes successfully uploaded to the database.")
