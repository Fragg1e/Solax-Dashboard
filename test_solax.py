from solax_client import SolaxClient
import os
from dotenv import load_dotenv
import json
import requests

# Load environment variables
load_dotenv()

def main():
    # Debug: Print environment variables
    print("Checking environment variables...")
    token = os.getenv('SOLAX_TOKEN_ID')
    wifi_sn = os.getenv('SOLAX_WIFI_SN')
    
    print(f"Raw token from .env: {repr(token)}")  # Show exact value
    print(f"Token length: {len(token) if token else 0}")

    if not token or len(token) < 10:  # Basic token length check
        raise ValueError("Token appears invalid (too short or empty)")

    print(f"SOLAX_TOKEN_ID: {'*****' if token else 'NOT SET'}")
    print(f"SOLAX_WIFI_SN: {wifi_sn or 'NOT SET'}")

    if not token or not wifi_sn:
        raise ValueError("Missing required environment variables")

    # Initialize client
    solax_client = SolaxClient(token_id=token)
    print(f"Client token: {repr(solax_client.token_id)}")  # Verify client received it
    print("\nClient initialized successfully")

    try:
        print("\nTesting real-time data...")
        print(f"Making request to: {solax_client.base_url}/getRealtimeInfo.do")
        print(f"With params: tokenId={token[:5]}...&sn={wifi_sn}")
        
        data = solax_client.get_realtime_data(wifi_sn)
        print("Full API Response:")
        print(json.dumps(data, indent=2))
        
        if not data.get('success'):
            print("\nAPI Error Details:")
            print(f"Code: {data.get('code')}")
            print(f"Message: {data.get('exception')}")
            print("Possible solutions:")
            print("- Verify your token is valid")
            print("- Check your WiFi serial number")
            print("- Ensure your inverter is online")

    except requests.exceptions.RequestException as e:
        print(f"\nNetwork error: {str(e)}")

if __name__ == "__main__":
    main() 