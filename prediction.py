import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime, timedelta
import os

MODEL_PATH = "solar_model.joblib"
SCALER_PATH = "scaler.joblib"


def prepare_features(df):
    # Convert date to datetime if it's not already
    df["date"] = pd.to_datetime(df["date"])

    # Extract date features
    df["day_of_year"] = df["date"].dt.dayofyear
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek

    return df[["day_of_year", "month", "day_of_week"]]


def train_model(df):
    # Prepare features
    X = prepare_features(df)
    y = df["solar"]

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train the model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)

    # Save the model and scaler
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    # Calculate and return the model score
    score = model.score(X_test_scaled, y_test)
    return score


def ensure_model_exists(df):
    """Ensure the model exists, train if it doesn't"""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        print("Training new model...")
        train_model(df)


def predict_next_days(days=7, df=None):
    """
    Predict solar generation for the next n days.
    If df is provided, ensure model is trained on this data first.
    """
    if df is not None:
        ensure_model_exists(df)

    try:
        # Load the model and scaler
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
    except FileNotFoundError:
        if df is None:
            return pd.DataFrame({"date": [], "predicted_solar": []})
        ensure_model_exists(df)
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)

    # Generate dates for prediction
    dates = [datetime.now() + timedelta(days=x) for x in range(days)]
    pred_df = pd.DataFrame({"date": dates})

    # Prepare features
    X_pred = prepare_features(pred_df)

    # Scale features and predict
    X_pred_scaled = scaler.transform(X_pred)
    predictions = model.predict(X_pred_scaled)

    # Create prediction results
    results = pd.DataFrame({"date": dates, "predicted_solar": predictions})

    return results
