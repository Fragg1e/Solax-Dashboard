import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

ELECTRICITY_RATE = 0.18  # 18 cents per kilowatt


def init_db():
    """Initialize the database connection"""
    try:
        logger.info("Initializing database connection")
        conn = sqlite3.connect("solar_data.db")
        c = conn.cursor()

        # Create table for solar data with financial columns
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS solar_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                solar FLOAT,
                feed_in FLOAT,
                grid FLOAT,
                consumption FLOAT,
                green_percentage FLOAT,
                money_saved FLOAT,
                money_earned_feed_in FLOAT,
                total_benefit FLOAT
            )
        """
        )

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False


def import_csv_data(file_path):
    """Import data from CSV file"""
    try:
        logger.info(f"Importing data from {file_path}")
        df = pd.read_csv(file_path)

        # Rename columns to match database schema
        column_mapping = {
            "Date": "date",
            "Solar": "solar",
            "Feed In": "feed_in",
            "Grid": "grid",
            "Consumption": "consumption",
            "% Green": "green_percentage",
        }
        df = df.rename(columns=column_mapping)

        # Convert date column to datetime with explicit format (DD/MM/YYYY)
        df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")

        # Convert numeric columns to standard Python float
        numeric_columns = [
            "solar",
            "feed_in",
            "grid",
            "consumption",
            "green_percentage",
        ]
        for col in numeric_columns:
            df[col] = df[col].astype(float)

        # Calculate financial metrics
        df["money_saved"] = df["solar"] * ELECTRICITY_RATE
        df["money_earned_feed_in"] = df["feed_in"] * ELECTRICITY_RATE
        df["total_benefit"] = df["money_saved"] + df["money_earned_feed_in"]

        # Insert data into the database
        conn = sqlite3.connect("solar_data.db")
        df.to_sql("solar_data", conn, if_exists="replace", index=False)
        conn.close()

        logger.info(f"Successfully imported {len(df)} records into database")
        return df
    except Exception as e:
        logger.error(f"Error importing CSV data: {str(e)}")
        return None


def get_all_data():
    """Get all solar data"""
    try:
        conn = sqlite3.connect("solar_data.db")
        query = """
            SELECT 
                date,
                solar as generation,
                grid as grid_import,
                feed_in as grid_export,
                0 as battery_charge,
                0 as battery_discharge
            FROM solar_data
            ORDER BY date DESC
        """
        df = pd.read_sql_query(query, conn, parse_dates=["date"])
        conn.close()

        if df.empty:
            # Return sample data if no data exists
            dates = pd.date_range(end=datetime.now(), periods=30)
            df = pd.DataFrame(
                {
                    "date": dates,
                    "generation": [0] * 30,
                    "grid_import": [0] * 30,
                    "grid_export": [0] * 30,
                    "battery_charge": [0] * 30,
                    "battery_discharge": [0] * 30,
                }
            )

        return df
    except Exception as e:
        logger.error(f"Error getting all data: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame instead of None


def get_recent_data(days=30):
    """Get recent solar data"""
    try:
        df = get_all_data()
        if df.empty:
            return df

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Filter data for the specified date range
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        recent_data = df.loc[mask].copy()

        if recent_data.empty:
            # Return sample data for the requested period
            dates = pd.date_range(start=start_date, end=end_date)
            recent_data = pd.DataFrame(
                {
                    "date": dates,
                    "generation": [0] * len(dates),
                    "grid_import": [0] * len(dates),
                    "grid_export": [0] * len(dates),
                    "battery_charge": [0] * len(dates),
                    "battery_discharge": [0] * len(dates),
                }
            )

        logger.info(f"Retrieved {len(recent_data)} records for the last {days} days")
        return recent_data
    except Exception as e:
        logger.error(f"Error getting recent data: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame instead of None


def get_financial_summary():
    """Get financial summary statistics"""
    try:
        df = get_all_data()
        if df.empty:
            return {
                "total_saved": 0,
                "total_earned": 0,
                "avg_daily_saved": 0,
                "best_day_benefit": 0,
            }

        return {
            "total_saved": df["money_saved"].sum(),
            "total_earned": df["money_earned_feed_in"].sum(),
            "avg_daily_saved": df["money_saved"].mean(),
            "best_day_benefit": df["total_benefit"].max(),
        }
    except Exception as e:
        logger.error(f"Error getting financial summary: {str(e)}")
        return {
            "total_saved": 0,
            "total_earned": 0,
            "avg_daily_saved": 0,
            "best_day_benefit": 0,
        }
