from flask import Flask, jsonify, request, render_template
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
from models import db, SolarData, BatteryData, InverterData, EVData

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up file handler
file_handler = RotatingFileHandler('logs/solax.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///solax.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

def get_mock_data():
    """Generate mock data for the dashboard."""
    data = {
        "solar": {
            "power": round(random.uniform(2, 5), 1),  # kW
            "daily": round(random.uniform(10, 25), 1),  # kWh
            "status": "active"
        },
        "battery": {
            "level": random.randint(20, 100),  # %
            "capacity": 13.5,  # kWh
            "status": "active"
        },
        "inverter": {
            "power": round(random.uniform(1, 4), 1),  # kW
            "efficiency": random.randint(85, 98),  # %
            "status": "active"
        },
        "ev": {
            "battery": random.randint(0, 100),  # %
            "range": random.randint(100, 400),  # km
            "status": "inactive"
        }
    }
    
    # Log the data
    logger.info(f"Generated mock data: {data}")
    
    # Store the data in the database
    with app.app_context():
        # Store solar data
        solar_data = SolarData(
            power=data['solar']['power'],
            daily_production=data['solar']['daily'],
            efficiency=random.uniform(90, 98)
        )
        db.session.add(solar_data)
        
        # Store battery data
        battery_data = BatteryData(
            charge_level=data['battery']['level'],
            power_flow=random.uniform(-2, 2),
            temperature=random.uniform(20, 30)
        )
        db.session.add(battery_data)
        
        # Store inverter data
        inverter_data = InverterData(
            power_output=data['inverter']['power'],
            efficiency=data['inverter']['efficiency'],
            temperature=random.uniform(30, 40)
        )
        db.session.add(inverter_data)
        
        # Store EV data
        ev_data = EVData(
            battery_level=data['ev']['battery'],
            charging_power=random.uniform(0, 7),
            estimated_range=data['ev']['range']
        )
        db.session.add(ev_data)
        
        db.session.commit()
    
    return data

@app.route('/')
def home():
    """Renders the homepage."""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the current status of all components."""
    return jsonify(get_mock_data())

@app.route('/api/historical/<component>', methods=['GET'])
def get_historical_data(component):
    """Returns historical data for a specific component."""
    hours = request.args.get('hours', 24, type=int)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    with app.app_context():
        if component == 'solar':
            data = SolarData.query.filter(
                SolarData.timestamp.between(start_time, end_time)
            ).all()
            return jsonify([{
                'timestamp': d.timestamp.isoformat(),
                'power': d.power,
                'daily_production': d.daily_production,
                'efficiency': d.efficiency
            } for d in data])
            
        elif component == 'battery':
            data = BatteryData.query.filter(
                BatteryData.timestamp.between(start_time, end_time)
            ).all()
            return jsonify([{
                'timestamp': d.timestamp.isoformat(),
                'charge_level': d.charge_level,
                'power_flow': d.power_flow,
                'temperature': d.temperature
            } for d in data])
            
        elif component == 'inverter':
            data = InverterData.query.filter(
                InverterData.timestamp.between(start_time, end_time)
            ).all()
            return jsonify([{
                'timestamp': d.timestamp.isoformat(),
                'power_output': d.power_output,
                'efficiency': d.efficiency,
                'temperature': d.temperature
            } for d in data])
            
        elif component == 'ev':
            data = EVData.query.filter(
                EVData.timestamp.between(start_time, end_time)
            ).all()
            return jsonify([{
                'timestamp': d.timestamp.isoformat(),
                'battery_level': d.battery_level,
                'charging_power': d.charging_power,
                'estimated_range': d.estimated_range
            } for d in data])
            
        else:
            return jsonify({'error': 'Invalid component'}), 400

@app.route('/api/control', methods=['POST'])
def control_device():
    """Handles control commands for devices."""
    command = request.json.get('command')
    
    # Log the command
    logger.info(f"Received control command: {command}")
    
    # Mock response based on command
    response = {
        "status": "success",
        "command": command,
        "timestamp": datetime.now().isoformat()
    }
    
    return jsonify(response)

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # In production, debug should be False
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug) 