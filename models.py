from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class SolarData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    power = db.Column(db.Float)  # kW
    daily_production = db.Column(db.Float)  # kWh
    efficiency = db.Column(db.Float)  # %

class BatteryData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    charge_level = db.Column(db.Float)  # %
    power_flow = db.Column(db.Float)  # kW (positive for charging, negative for discharging)
    temperature = db.Column(db.Float)  # °C

class InverterData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    power_output = db.Column(db.Float)  # kW
    efficiency = db.Column(db.Float)  # %
    temperature = db.Column(db.Float)  # °C

class EVData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    battery_level = db.Column(db.Float)  # %
    charging_power = db.Column(db.Float)  # kW
    estimated_range = db.Column(db.Float)  # km 