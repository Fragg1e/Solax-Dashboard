from solax_client import SolaxClient
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def test_solax_connection():
    # Get credentials from environment
    token_id = os.getenv('SOLAX_TOKEN_ID')
    wifi_sn = os.getenv('SOLAX_WIFI_SN')
    
    print("\nTesting Solax API Connection")
    print("============================")
    print(f"Token ID: {'*' * len(token_id) if token_id else 'Not set'}")
    print(f"WiFi SN: {wifi_sn if wifi_sn else 'Not set'}")
    
    if not token_id or not wifi_sn:
        print("\nError: Missing credentials!")
        print("Please set SOLAX_TOKEN_ID and SOLAX_WIFI_SN in your .env file")
        return
    
    try:
        # Initialize client
        client = SolaxClient(token_id=token_id)
        
        # Get real-time data
        print("\nFetching real-time data...")
        response = client.get_realtime_data(wifi_sn)
        
        # Print raw response
        print("\nRaw API Response:")
        print(json.dumps(response, indent=2))
        
        if response["success"]:
            data = response["result"]
            print("\nProcessed Data:")
            print("==============")
            print(f"Inverter SN: {data.get('inverterSN', 'N/A')}")
            print(f"WiFi SN: {data.get('sn', 'N/A')}")
            print(f"AC Power: {data.get('acpower', 0)}W")
            print(f"Today's Yield: {data.get('yieldtoday', 0)}kWh")
            print(f"Total Yield: {data.get('yieldtotal', 0)}kWh")
            print(f"Grid Export: {data.get('feedinpower', 0)}W")
            print(f"Battery SOC: {data.get('soc', 'N/A')}%")
            print(f"Inverter Status: {client.get_inverter_status_text(data.get('inverterStatus', '0'))}")
            print(f"Battery Status: {client.get_battery_status_text(data.get('batStatus', '0'))}")
            print(f"PV1 Power: {data.get('powerdc1', 0)}W")
            print(f"PV2 Power: {data.get('powerdc2', 0)}W")
            print(f"Last Update: {data.get('uploadTime', 'N/A')}")
        else:
            print("\nError:", response.get("exception", "Unknown error"))
            print("Code:", response.get("code", "Unknown code"))
            
    except Exception as e:
        print("\nError connecting to Solax API:")
        print(str(e))

if __name__ == "__main__":
    test_solax_connection() 