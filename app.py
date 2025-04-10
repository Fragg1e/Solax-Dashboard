from flask import Flask, jsonify
import os
from solax_client import SolaxClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize client exactly like in test_solax.py
solax_client = SolaxClient(token_id=os.getenv('SOLAX_TOKEN_ID'))

@app.route('/')
def status():
    try:
        wifi_sn = os.getenv('SOLAX_WIFI_SN')
        if not wifi_sn:
            return jsonify({'error': 'SOLAX_WIFI_SN not configured'}), 500
            
        data = solax_client.get_realtime_data(wifi_sn)
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 