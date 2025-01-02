import sqlite3

# Define database connection and cursor
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

try:
    # Create URLs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urls (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      url TEXT NOT NULL UNIQUE
    );
    """)

    # Create commodity_code table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS commodity_code (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      hs_code VARCHAR,
      description TEXT,
      code VARCHAR
    );
    """)

    # Commit changes
    connection.commit()
    print("Tables successfully created in the database.")

except sqlite3.Error as e:
    print("Error creating tables:", e)

finally:
    # Close connection
    connection.close()
