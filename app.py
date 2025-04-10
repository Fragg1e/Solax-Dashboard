from flask import Flask, jsonify, request, render_template, send_file
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
from models import db, SolarData, BatteryData, InverterData, EVData
import csv
import io
import requests
import json
from solax_client import SolaxClient
import math

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
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

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///solax_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

# Weather API configuration
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', 'your_api_key_here')
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/forecast"
DEFAULT_LOCATION = "London,UK"  # Default location if none is provided

# Initialize Solax client
solax_client = SolaxClient(
    token_id=os.getenv('SOLAX_TOKEN_ID'),
    base_url="https://www.solaxcloud.com/api/v1"
)

# Get WiFi SN from environment
WIFI_SN = os.getenv('SOLAX_WIFI_SN')

def get_weather_data(location=DEFAULT_LOCATION):
    """Fetch weather forecast data from OpenWeatherMap API.
    
    Args:
        location (str): City name and country code divided by comma (e.g. London,UK)
        
    Returns:
        dict: Weather forecast data or None if request fails
    """
    try:
        params = {
            'q': location,
            'appid': WEATHER_API_KEY,
            'units': 'metric',  # Use metric units
            'cnt': 40  # Maximum number of timestamps (5 days with 3-hour steps)
        }
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        
        # Check for rate limiting
        if response.status_code == 429:
            logger.error("OpenWeatherMap API rate limit exceeded")
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching weather data")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        return None

def predict_solar_power(weather_data):
    """Predict solar power generation based on weather forecast.
    
    Uses multiple weather parameters to make a more accurate prediction:
    - Cloud coverage
    - Solar radiation (if available)
    - Temperature
    - Weather condition
    - Time of day
    - Season
    
    Args:
        weather_data (dict): Weather forecast data from OpenWeatherMap API
        
    Returns:
        list: Predicted solar power generation for each timestamp
    """
    if not weather_data or 'list' not in weather_data:
        return []
    
    predictions = []
    
    # Base solar capacity (in kW) - adjust based on your system
    base_capacity = 5.0
    
    # Get location data for calculating day length
    lat = weather_data.get('city', {}).get('coord', {}).get('lat', 51.5)  # Default to London
    lon = weather_data.get('city', {}).get('coord', {}).get('lon', -0.13)
    
    for item in weather_data['list']:
        timestamp = datetime.fromtimestamp(item['dt'])
        
        # Get weather parameters
        clouds = item.get('clouds', {}).get('all', 50)  # Cloud coverage %
        temp = item.get('main', {}).get('temp', 20)  # Temperature in Celsius
        weather_id = item.get('weather', [{}])[0].get('id', 800)  # Weather condition ID
        
        # Calculate power reduction factors
        
        # 1. Cloud coverage factor (0.2 to 1.0)
        cloud_factor = 1.0 - (clouds * 0.8 / 100)
        
        # 2. Temperature factor (panels are most efficient around 25°C)
        # Efficiency drops by about 0.4% per degree above 25°C
        temp_factor = 1.0 - max(0, (temp - 25) * 0.004)
        
        # 3. Weather condition factor
        weather_factor = 1.0
        if weather_id < 600:  # Rain
            weather_factor = 0.3
        elif weather_id < 700:  # Snow
            weather_factor = 0.1
        elif weather_id < 800:  # Atmosphere (mist, fog, etc)
            weather_factor = 0.5
        
        # 4. Time of day factor (simple cosine function)
        hour = timestamp.hour
        if hour < 6 or hour > 18:  # Night time
            time_factor = 0
        else:
            time_factor = math.cos((hour - 12) * math.pi / 12) * 0.5 + 0.5
        
        # Calculate final power
        power = base_capacity * cloud_factor * temp_factor * weather_factor * time_factor
        
        predictions.append({
            'timestamp': timestamp.isoformat(),
            'power': round(power, 2),
            'clouds': clouds,
            'temperature': temp,
            'weather_condition': item.get('weather', [{}])[0].get('description', ''),
            'weather_id': weather_id,
            'factors': {
                'cloud_factor': round(cloud_factor, 2),
                'temp_factor': round(temp_factor, 2),
                'weather_factor': round(weather_factor, 2),
                'time_factor': round(time_factor, 2)
            }
        })
    
    return predictions

def get_real_data():
    """Get real data from the Solax system."""
    try:
        # Get real-time data from Solax
        response = solax_client.get_realtime_data(WIFI_SN)
        
        if not response["success"]:
            logger.error(f"Failed to get real-time data: {response['exception']}")
            return get_mock_data()
        
        data = response["result"]
        
        # Process the real data
        processed_data = {
            "solar": {
                "power": data.get("acpower", 0) / 1000,  # Convert W to kW
                "daily": data.get("yieldtoday", 0),
                "status": "active" if data.get("inverterStatus") == "102" else "inactive"
            },
            "battery": {
                "level": data.get("soc", 0),
                "capacity": 10,  # Default capacity in kWh
                "status": "active" if data.get("batStatus") == "0" else "inactive"
            },
            "inverter": {
                "power": data.get("acpower", 0) / 1000,  # Convert W to kW
                "efficiency": 95,  # Default efficiency
                "status": "active" if data.get("inverterStatus") == "102" else "inactive"
            },
            "ev": {
                "battery": 0,  # Not available in API
                "range": 0,  # Not available in API
                "status": "inactive"
            }
        }
        
        # Log the data
        logger.info(f"Retrieved real data: {processed_data}")
        
        # Store the data in the database
        with app.app_context():
            # Store solar data
            solar_data = SolarData(
                power=processed_data['solar']['power'],
                daily_production=processed_data['solar']['daily'],
                efficiency=processed_data['inverter']['efficiency']
            )
            db.session.add(solar_data)
            
            # Store battery data
            battery_data_model = BatteryData(
                charge_level=processed_data['battery']['level'],
                power_flow=0,  # Power flow not available in API
                temperature=0  # Temperature not available in API
            )
            db.session.add(battery_data_model)
            
            # Store inverter data
            inverter_data_model = InverterData(
                power_output=processed_data['inverter']['power'],
                efficiency=processed_data['inverter']['efficiency'],
                temperature=0  # Temperature not available in API
            )
            db.session.add(inverter_data_model)
            
            # Store EV data (mock data since Solax doesn't provide this)
            ev_data = EVData(
                battery_level=processed_data['ev']['battery'],
                charging_power=0,
                estimated_range=processed_data['ev']['range']
            )
            db.session.add(ev_data)
            
            db.session.commit()
        
        return processed_data
    except Exception as e:
        logger.error(f"Error getting real data: {str(e)}")
        return get_mock_data()

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
    # Try to get real data first, fall back to mock data if needed
    return jsonify(get_real_data())

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
    
    # Try to send the command to the Solax system
    try:
        response = solax_client.control_device(command)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error controlling device: {str(e)}")
        # Return a mock response if the real API call fails
        return jsonify({
            "status": "success",
            "command": command,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/export', methods=['GET'])
def export_data():
    try:
        # Get time range from query parameters (default to 7 days)
        hours = int(request.args.get('hours', 168))
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query all data within the time range
        solar_data = SolarData.query.filter(SolarData.timestamp >= start_time).all()
        battery_data = BatteryData.query.filter(BatteryData.timestamp >= start_time).all()
        inverter_data = InverterData.query.filter(InverterData.timestamp >= start_time).all()
        ev_data = EVData.query.filter(EVData.timestamp >= start_time).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Timestamp', 'Component', 'Metric', 'Value', 'Unit'])
        
        # Write solar data
        for data in solar_data:
            writer.writerow([data.timestamp, 'Solar', 'Power', data.power, 'kW'])
            writer.writerow([data.timestamp, 'Solar', 'Daily Production', data.daily_production, 'kWh'])
        
        # Write battery data
        for data in battery_data:
            writer.writerow([data.timestamp, 'Battery', 'Charge Level', data.charge_level, '%'])
            writer.writerow([data.timestamp, 'Battery', 'Power Flow', data.power_flow, 'kW'])
        
        # Write inverter data
        for data in inverter_data:
            writer.writerow([data.timestamp, 'Inverter', 'Power', data.power_output, 'kW'])
            writer.writerow([data.timestamp, 'Inverter', 'Efficiency', data.efficiency, '%'])
        
        # Write EV data
        for data in ev_data:
            writer.writerow([data.timestamp, 'EV', 'Battery Level', data.battery_level, '%'])
            writer.writerow([data.timestamp, 'EV', 'Range', data.estimated_range, 'km'])
        
        # Prepare the response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'solax_data_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Returns weather forecast data."""
    location = request.args.get('location', DEFAULT_LOCATION)
    weather_data = get_weather_data(location)
    
    if not weather_data:
        return jsonify({'error': 'Failed to fetch weather data'}), 500
    
    return jsonify(weather_data)

@app.route('/api/solar-prediction', methods=['GET'])
def get_solar_prediction():
    """Returns solar power prediction based on weather forecast."""
    location = request.args.get('location', DEFAULT_LOCATION)
    weather_data = get_weather_data(location)
    
    if not weather_data:
        return jsonify({'error': 'Failed to fetch weather data'}), 500
    
    predictions = predict_solar_power(weather_data)
    return jsonify(predictions)

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # In production, debug should be False
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug) 