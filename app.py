from flask import Flask, jsonify
import os
from solax_client import SolaxClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize Solax client only
solax_client = SolaxClient(
    token_id=os.getenv('SOLAX_TOKEN_ID'),
    wifi_sn=os.getenv('SOLAX_WIFI_SN')
)

@app.route('/api/status')
def get_status():
    try:
        # Get real-time data only
        data = solax_client.get_realtime_data()
        return jsonify({
            'status': 'online',
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/live')
def get_live_data():
    try:
        return jsonify(solax_client.get_realtime_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 