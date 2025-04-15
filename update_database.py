import pandas as pd
import sqlite3
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_database():
    try:
        # Read the CSV file
        logger.info("Reading CSV file...")
        df = pd.read_csv("history_solar_data.csv")

        # Rename columns to match database schema
        df = df.rename(
            columns={
                "Date": "date",
                "Solar": "solar",
                "Feed In": "feed_in",
                "Grid": "grid",
                "Consumption": "consumption",
                "% Green": "green_percentage",
            }
        )

        # Convert date to datetime
        df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")

        # Calculate financial metrics
        ELECTRICITY_RATE = 0.18  # 18 cents per kilowatt
        df["money_saved"] = df["solar"] * ELECTRICITY_RATE
        df["money_earned_feed_in"] = df["feed_in"] * ELECTRICITY_RATE
        df["total_benefit"] = df["money_saved"] + df["money_earned_feed_in"]

        # Connect to database
        logger.info("Connecting to database...")
        conn = sqlite3.connect("solar_data.db")

        # Clear existing data
        logger.info("Clearing existing data...")
        conn.execute("DELETE FROM solar_data")

        # Insert new data
        logger.info("Inserting new data...")
        df.to_sql("solar_data", conn, if_exists="append", index=False)

        # Commit changes and close connection
        conn.commit()
        conn.close()

        logger.info("Database update completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        return False


if __name__ == "__main__":
    update_database()
