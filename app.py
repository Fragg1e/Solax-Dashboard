from flask import Flask, jsonify, render_template
import os
from solax_client import SolaxClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize Solax client
solax_client = SolaxClient(token_id=os.getenv('SOLAX_TOKEN_ID'))

@app.route('/')
def dashboard():
    try:
        wifi_sn = os.getenv('SOLAX_WIFI_SN')
        if not wifi_sn:
            return render_template('error.html', message="SOLAX_WIFI_SN not configured")
            
        data = solax_client.get_realtime_data(wifi_sn)
        if not data.get('success'):
            return render_template('error.html', message=data.get('exception', 'API Error'))
            
        return render_template('index.html', 
            ac_power=data['result']['acpower'],
            yield_today=data['result']['yieldtoday'],
            battery_soc=data['result']['soc'],
            feed_in_power=data['result']['feedinpower']
        )
        
    except Exception as e:
        return render_template('error.html', message=str(e))

@app.route('/api/status')
def get_status():
    try:
        wifi_sn = os.getenv('SOLAX_WIFI_SN')
        data = solax_client.get_realtime_data(wifi_sn)
        return jsonify(data['result'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical/<component>')
def get_historical_data(component):
    # Placeholder for historical data
    return jsonify([])

@app.route('/api/weather')
def get_weather():
    # Placeholder for weather data
    return jsonify([])

@app.route('/api/solar-prediction')
def get_solar_prediction():
    # Placeholder for solar prediction data
    return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 