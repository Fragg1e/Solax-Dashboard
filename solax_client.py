import requests
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SolaxClient:
    """Client for interacting with Solax API v2.0."""
    
    def __init__(self, token_id=None, base_url="https://www.solaxcloud.com/proxyApp/proxy/api"):
        """Initialize the Solax client.
        
        Args:
            token_id (str, optional): Solax API token ID. Defaults to None.
            base_url (str, optional): Base URL for the Solax API. Defaults to "https://www.solaxcloud.com/proxyApp/proxy/api".
        """
        self.token_id = token_id or os.environ.get('SOLAX_TOKEN_ID')
        if not self.token_id:
            raise ValueError("Token ID is required. Set SOLAX_TOKEN_ID environment variable or pass token_id parameter.")
            
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Token-Id': self.token_id
        })
    
    def get_system_info(self):
        """Get information about the Solax system."""
        try:
            response = self.session.get(f"{self.base_url}/inverter/getBasicInfo.do")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching system info: {str(e)}")
            return None
    
    def get_realtime_data(self, wifi_sn):
        """Get real-time data from the Solax system.
        
        Args:
            wifi_sn (str): WiFi module serial number (registration number)
            
        Returns:
            dict: Response containing real-time data including:
                - inverterSN: Inverter serial number
                - sn: WiFi module serial number
                - acpower: AC output power (W)
                - yieldtoday: Today's yield (kWh)
                - yieldtotal: Total yield (kWh)
                - feedinpower: Power supplied to the grid (W)
                - feedinenergy: Total grid export power (kWh)
                - consumeenergy: Total grid import power (kWh)
                - feedinpowerM2: Meter 2 power (W)
                - soc: Battery capacity (%)
                - peps1: EPS A phase active power (W)
                - peps2: EPS B phase active power (W)
                - peps3: EPS C phase active power (W)
                - inverterType: Inverter type
                - inverterStatus: Inverter operating conditions
                - uploadTime: Upload time (format: YYYY-MM-DD HH:MM:SS)
                - batPower: Battery terminal power (W)
                - powerdc1: PV1 input power (W)
                - powerdc2: PV2 input power (W)
                - powerdc3: PV3 input power (W)
                - powerdc4: PV4 input power (W)
                - batStatus: Battery status (0=normal, 1=fault, 2=disconnected)
        """
        try:
            params = {
                'tokenId': self.token_id,
                'sn': wifi_sn
            }
            response = self.session.get(
                f"{self.base_url}/getRealtimeInfo.do",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching realtime data: {str(e)}")
            return {
                "success": False,
                "exception": str(e),
                "result": None,
                "code": 2001  # Operation failed
            }
    
    def get_daily_data(self, date=None):
        """Get daily data from the Solax system.
        
        Args:
            date (str, optional): Date in YYYY-MM-DD format. Defaults to today.
            
        Returns:
            dict: Daily data including:
                - date: Date of the data
                - energy: Total energy produced (kWh)
                - peak_power: Peak power reached (kW)
                - peak_time: Time of peak power
                - self_consumption: Self-consumption rate (%)
                - grid_import: Grid import (kWh)
                - grid_export: Grid export (kWh)
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = self.session.get(f"{self.base_url}/daily", params={'date': date})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching daily data: {str(e)}")
            return None
    
    def get_historical_data(self, start_time, end_time=None):
        """Get historical data from the Solax system.
        
        Args:
            start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'
            end_time (str, optional): End time in format 'YYYY-MM-DD HH:MM:SS'. Defaults to current time.
        """
        try:
            if end_time is None:
                end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            data = {
                'tokenId': self.token_id,
                'startTime': start_time,
                'endTime': end_time
            }
            
            response = self.session.post(
                f"{self.base_url}/inverter/getHistoryInfo.do",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return None
    
    def get_battery_data(self):
        """Get battery data from the Solax system.
        
        Returns:
            dict: Battery data including:
                - soc: State of charge (%)
                - power: Current power (kW)
                - voltage: Battery voltage (V)
                - current: Battery current (A)
                - temperature: Battery temperature (°C)
                - status: Battery status
                - cycle_count: Number of charge cycles
                - capacity: Nominal capacity (kWh)
                - health: Battery health (%)
        """
        try:
            response = self.session.get(f"{self.base_url}/battery")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching battery data: {str(e)}")
            return None
    
    def get_inverter_data(self):
        """Get inverter data from the Solax system.
        
        Returns:
            dict: Inverter data including:
                - power: Current power output (kW)
                - voltage: Output voltage (V)
                - current: Output current (A)
                - frequency: Output frequency (Hz)
                - temperature: Inverter temperature (°C)
                - efficiency: Current efficiency (%)
                - status: Inverter status
                - error_code: Error code if any
                - total_energy: Total energy produced (kWh)
        """
        try:
            response = self.session.get(f"{self.base_url}/inverter")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching inverter data: {str(e)}")
            return None
    
    def control_device(self, command, params=None):
        """Send a control command to the Solax system.
        
        Args:
            command (str): Command to send. Valid commands:
                - start_charging: Start battery charging
                - stop_charging: Stop battery charging
                - start_discharging: Start battery discharging
                - stop_discharging: Stop battery discharging
                - set_charge_limit: Set battery charge limit
                - set_discharge_limit: Set battery discharge limit
                - set_power_mode: Set power mode (grid/off-grid)
            params (dict, optional): Parameters for the command. Defaults to None.
                For set_charge_limit: {'limit': percentage}
                For set_discharge_limit: {'limit': percentage}
                For set_power_mode: {'mode': 'grid' or 'off-grid'}
            
        Returns:
            dict: Response from the API including:
                - status: 'success' or 'error'
                - message: Response message
                - command: Executed command
                - timestamp: Command execution time
        """
        try:
            data = {
                'tokenId': self.token_id,
                'command': command
            }
            if params:
                data.update(params)
            
            response = self.session.post(
                f"{self.base_url}/inverter/setControl.do",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending control command: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def get_inverter_status_text(self, status_code):
        """Get human-readable inverter status from status code."""
        status_map = {
            "100": "Waiting",
            "101": "Checking",
            "102": "Normal",
            "103": "Fault",
            "104": "Permanent Fault",
            "105": "Updating",
            "106": "EPS Check",
            "107": "EPS Mode",
            "108": "Self Test",
            "109": "Idle",
            "110": "Standby",
            "111": "Pv Wake Up Battery Mode",
            "112": "Gen Check",
            "113": "Gen Run",
            "114": "Soft Start"
        }
        return status_map.get(str(status_code), "Unknown")
    
    def get_battery_status_text(self, status_code):
        """Get human-readable battery status from status code."""
        status_map = {
            "0": "Normal",
            "1": "Fault",
            "2": "Disconnected",
            "3": "Sleep Mode",
            "4": "Charging",
            "5": "Discharging"
        }
        return status_map.get(str(status_code), "Unknown")
    
    def get_error_message(self, error_code):
        """Get human-readable error message from error code.
        
        Args:
            error_code (int): Error code
            
        Returns:
            str: Human-readable error message
        """
        error_map = {
            1001: "Interface Unauthorized",
            1002: "Parameter validation failed",
            1003: "Data Unauthorized",
            1004: "Duplicate data",
            2001: "Operation failed",
            2002: "Data not found"
        }
        return error_map.get(error_code, "Unknown error")

# For testing
if __name__ == "__main__":
    client = SolaxClient()
    wifi_sn = os.getenv('SOLAX_WIFI_SN')
    if wifi_sn:
        result = client.get_realtime_data(wifi_sn)
        print("\nRealtime Data:")
        print(json.dumps(result, indent=2))
        
        if result.get("success") and result.get("result"):
            data = result["result"]
            print(f"\nInverter Status: {client.get_inverter_status_text(data.get('inverterStatus'))}")
            print(f"Battery Status: {client.get_battery_status_text(data.get('batStatus'))}")
            print(f"AC Power: {data.get('acpower')}W")
            print(f"Today's Yield: {data.get('yieldtoday')}kWh")
            print(f"Battery Level: {data.get('soc')}%") 