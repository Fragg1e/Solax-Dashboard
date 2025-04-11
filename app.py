from flask import Flask, jsonify, render_template, flash, redirect, url_for
import os
from solax_client import SolaxClient
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Initialize Solax client
solax_client = SolaxClient(token_id=os.getenv('SOLAX_TOKEN_ID'))

logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def dashboard():
    try:
        wifi_sn = os.getenv('SOLAX_WIFI_SN')
        if not wifi_sn:
            flash("SOLAX_WIFI_SN not configured", "error")
            return render_template('index.html')
            
        data = solax_client.get_realtime_data(wifi_sn)
        logging.debug(f"Solax API response: {data}")
        if not data.get('success'):
            flash(data.get('exception', 'API Error'), "error")
            return render_template('index.html')
            
        return render_template('index.html', 
            ac_power=data['result']['acpower'],
            yield_today=data['result']['yieldtoday'],
            battery_soc=data['result']['soc'],
            feed_in_power=data['result']['feedinpower']
        )
        
    except Exception as e:
        logging.error(f"Error: {e}")
        flash(str(e), "error")
        return render_template('index.html')

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