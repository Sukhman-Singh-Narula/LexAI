#!/usr/bin/env python
import os
import time
from dotenv import load_dotenv
from sqlalchemy import text
from database import engine, Base

load_dotenv()

def reset_database():
    with engine.begin() as connection:
        # Disable foreign key checks
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        print("Dropping all tables...")
        Base.metadata.drop_all(connection)
        print("All tables dropped successfully.")
        # Re-enable foreign key checks
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    
    # Dispose engine to close lingering connections
    engine.dispose()
    time.sleep(2)  # Wait a bit for MySQL to finish DDL operations

    print("Creating all tables...")
    Base.metadata.create_all(engine)
    print("Database reset successfully.")

if __name__ == "__main__":
    reset_database()
