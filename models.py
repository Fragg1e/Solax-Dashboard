from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class SolarData(db.Model):
    __tablename__ = 'solar_data'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    power = db.Column(db.Float)  # Current power in watts
    daily_yield = db.Column(db.Float)  # kWh
    
    def __repr__(self):
        return f'<SolarData {self.timestamp}: {self.power}W>'

class BatteryData(db.Model):
    __tablename__ = 'battery_data'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    soc = db.Column(db.Float)  # State of charge (0-100)
    power = db.Column(db.Float)  # Charge/discharge power (W)

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