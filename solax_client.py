import requests
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SolaxClient:
    """Client for interacting with Solax API."""
    
    def __init__(self, token_id=None, base_url="https://www.solaxcloud.com/api/v1"):
        """Initialize the Solax client.
        
        Args:
            token_id (str, optional): Solax API token ID. Defaults to None.
            base_url (str, optional): Base URL for the Solax API. Defaults to "https://www.solaxcloud.com/api/v1".
        """
        self.token_id = token_id or os.environ.get('SOLAX_TOKEN_ID')
        if not self.token_id:
            raise ValueError("Token ID is required. Set SOLAX_TOKEN_ID environment variable or pass token_id parameter.")
            
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def get_system_info(self):
        """Get information about the Solax system.
        
        Returns:
            dict: System information including:
                - serial_number: System serial number
                - model: System model
                - firmware_version: Current firmware version
                - grid_voltage: Grid voltage (V)
                - grid_frequency: Grid frequency (Hz)
                - total_energy: Total energy produced (kWh)
                - today_energy: Today's energy production (kWh)
                - total_power: Current total power (kW)
                - status: System status
        """
        try:
            response = self.session.get(f"{self.base_url}/system/info")
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
            dict: Response containing real-time data
        """
        try:
            params = {
                "tokenId": self.token_id,
                "sn": wifi_sn
            }
            response = self.session.get(
                f"{self.base_url}/realTimeData.do",
                params=params
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
    
    def get_historical_data(self, start_date, end_date=None):
        """Get historical data from the Solax system.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format.
            end_date (str, optional): End date in YYYY-MM-DD format. Defaults to today.
            
        Returns:
            dict: Historical data including:
                - daily_data: List of daily data points
                - total_energy: Total energy produced in period (kWh)
                - average_daily_energy: Average daily energy (kWh)
                - peak_power: Peak power reached (kW)
                - self_consumption_rate: Average self-consumption rate (%)
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = self.session.get(
                f"{self.base_url}/historical", 
                params={'start_date': start_date, 'end_date': end_date}
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
            data = {'command': command}
            if params:
                data.update(params)
            
            response = self.session.post(f"{self.base_url}/control", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending control command: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def get_inverter_status_text(self, status_code):
        """Get human-readable inverter status from status code.
        
        Args:
            status_code (str): Inverter status code
            
        Returns:
            str: Human-readable status description
        """
        status_map = {
            "100": "Waiting for operation",
            "101": "Self-test",
            "102": "Normal",
            "103": "Recoverable fault",
            "104": "Permanent fault",
            "105": "Firmware upgrade",
            "106": "EPS detection",
            "107": "Off-grid",
            "108": "Self-test mode (Italian safety regulations)",
            "109": "Sleep mode",
            "110": "Standby mode",
            "111": "Photovoltaic wake-up battery mode",
            "112": "Generator detection mode",
            "113": "Generator mode",
            "114": "Fast shutdown standby mode",
            "130": "VPP mode",
            "131": "TOU-Self use",
            "132": "TOU-Charging",
            "133": "TOU-Discharging"
        }
        return status_map.get(status_code, "Unknown status")
    
    def get_battery_status_text(self, status_code):
        """Get human-readable battery status from status code.
        
        Args:
            status_code (str): Battery status code
            
        Returns:
            str: Human-readable status description
        """
        status_map = {
            "0": "Normal",
            "1": "Fault",
            "2": "Disconnected"
        }
        return status_map.get(status_code, "Unknown status")
    
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
    # Example usage with a WiFi serial number
    result = client.get_realtime_data("SUT****VB1")
    print("Realtime Data:", result)
    
    if result["success"] and result["result"]:
        data = result["result"]
        print(f"Inverter Status: {client.get_inverter_status_text(data['inverterStatus'])}")
        if data["batStatus"] is not None:
            print(f"Battery Status: {client.get_battery_status_text(data['batStatus'])}") 