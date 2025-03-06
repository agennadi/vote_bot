import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

polls_db = os.getenv("POLLS_DB")

# Connect to the SQLite database
conn = sqlite3.connect(polls_db)  # Replace with your actual database file
cursor = conn.cursor()

print("polls:")
# Execute a query to select data from a table
cursor.execute("SELECT * FROM polls")  # Example query to select all columns from 'polls' table

# Fetch all results (you can also use fetchone() or fetchmany())
rows = cursor.fetchall()

# Process the results
for row in rows:
    print(row)  # Each row is a tuple containing the data for that record


print("poll options:")
cursor.execute("SELECT * FROM poll_options") 
rows = cursor.fetchall()

# Process the results
for row in rows:
    print(row)  # Each row is a tuple containing the data for that record

print("votes:")
cursor.execute("SELECT * FROM votes") 
rows = cursor.fetchall()

# Process the results
for row in rows:
    print(row)  # Each row is a tuple containing the data for that record


# Close the connection when done
conn.close()