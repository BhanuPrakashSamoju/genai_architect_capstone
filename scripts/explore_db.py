import sqlite3
 
def load_database(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    print(f"Connected to database: {db_path}")
 
    # Create a cursor object
    cursor = conn.cursor()
 
    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in the database:")
    for table in tables:
        print(f"- {table[0]}")

        # Fetch & print the table schema
        cursor.execute(f"PRAGMA table_info({table[0]});")
        schema = cursor.fetchall()
        print(f"  Schema: {schema}")
        
        # Fetch & print a sample of data
        sample_data = cursor.execute(f"SELECT * FROM {table[0]} LIMIT 10;").fetchall()
        print(f"  Sample data: {sample_data}")
        
 
    # Close the connection
    conn.close()
    print("Connection closed.")
 
if __name__ == "__main__":
    db_file = "dataset/LoanDB_BlueLoans4all.sqlite"
    load_database(db_file)