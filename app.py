from flask import Flask, jsonify, request, render_template
import random
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

def get_mock_data():
    """Generate mock data for the dashboard."""
    return {
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

@app.route('/')
def home():
    """Renders the homepage."""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the current status of all components."""
    return jsonify(get_mock_data())

@app.route('/api/control', methods=['POST'])
def control_device():
    """Handles control commands for devices."""
    command = request.json.get('command')
    
    # Mock response based on command
    response = {
        "status": "success",
        "command": command,
        "timestamp": datetime.now().isoformat()
    }
    
    # In a real implementation, you would:
    # 1. Validate the command
    # 2. Send it to the appropriate device
    # 3. Wait for confirmation
    # 4. Return the actual result
    
    return jsonify(response)

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # In production, debug should be False
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug) 