import requests
import logging
import hashlib
import time
from typing import Dict, Optional
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger(__name__)


class MyEnergiAPI:
    def __init__(self, serial_number: str, password: str):
        """Initialize MyEnergi API client

        Args:
            serial_number: The hub serial number (used as username)
            password: The password set in the app
        """
        self.serial_number = serial_number
        self.password = password
        self.base_url = (
            "https://s18.myenergi.net"  # Using s18 directly as it worked before
        )
        logger.info(f"Initializing MyEnergi API with serial number: {serial_number}")

    def _generate_digest_auth(self, url: str, method: str = "GET") -> Dict[str, str]:
        """Generate Digest Authentication header"""
        try:
            # Initial request to get WWW-Authenticate header
            response = requests.get(url)
            logger.debug(f"Initial response status: {response.status_code}")
            logger.debug(f"Initial response headers: {response.headers}")

            if response.status_code != 401:
                logger.error(f"Expected 401 status code, got {response.status_code}")
                return {}

            www_auth = response.headers.get("www-authenticate", "")
            logger.debug(f"WWW-Authenticate header: {www_auth}")

            if not www_auth:
                logger.error("No WWW-Authenticate header found")
                return {}

            # Parse WWW-Authenticate header
            auth_parts = {}

            # Remove "Digest " prefix if present
            if www_auth.startswith("Digest "):
                www_auth = www_auth[7:]

            # Split by comma and parse each key-value pair
            for part in www_auth.split(","):
                part = part.strip()
                if "=" in part:
                    key, value = part.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    auth_parts[key] = value

            logger.debug(f"Parsed auth parts: {auth_parts}")

            realm = auth_parts.get("realm", "")
            nonce = auth_parts.get("nonce", "")
            qop = (
                auth_parts.get("qop", "").split(",")[0] if "qop" in auth_parts else None
            )

            if not realm or not nonce:
                logger.error(f"Missing realm or nonce. Realm: {realm}, Nonce: {nonce}")
                return {}

            # Generate cnonce (client nonce)
            cnonce = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
            nc = "00000001"  # nonce count
            uri = urlparse(url).path

            # Calculate HA1 = MD5(username:realm:password)
            ha1 = hashlib.md5(
                f"{self.serial_number}:{realm}:{self.password}".encode()
            ).hexdigest()
            logger.debug(f"HA1: {ha1}")

            # Calculate HA2 = MD5(method:uri)
            ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
            logger.debug(f"HA2: {ha2}")

            # Calculate response
            if qop:
                response = hashlib.md5(
                    f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
                ).hexdigest()
            else:
                response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

            logger.debug(f"Response: {response}")

            # Build Authorization header
            auth_header = [
                f'Digest username="{self.serial_number}"',
                f'realm="{realm}"',
                f'nonce="{nonce}"',
                f'uri="{uri}"',
            ]

            if qop:
                auth_header.extend(
                    [
                        f"qop={qop}",
                        f"nc={nc}",
                        f'cnonce="{cnonce}"',
                    ]
                )

            auth_header.append(f'response="{response}"')

            final_header = ", ".join(auth_header)
            logger.debug(f"Final Authorization header: {final_header}")

            return {"Authorization": final_header}
        except Exception as e:
            logger.error(f"Error generating digest auth: {str(e)}")
            return {}

    def _make_request(self, endpoint: str) -> Dict:
        """Make a request to the MyEnergi API with error handling"""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"Making request to: {url}")

            # Get digest auth header
            headers = self._generate_digest_auth(url)
            if not headers:
                return {
                    "success": False,
                    "error": "Failed to generate authentication header",
                }

            logger.debug(f"Using headers: {headers}")
            response = requests.get(url, headers=headers, timeout=10)

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")

            if response.status_code == 401:
                logger.error("Authentication failed")
                return {"success": False, "error": "Authentication failed"}

            response.raise_for_status()

            data = response.json()
            logger.debug(f"Response data: {data}")

            return {"success": True, "data": data}
        except requests.exceptions.Timeout:
            error_msg = f"Timeout connecting to {url}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_eddi_data(self) -> Dict:
        """Fetch data from Eddi device"""
        return self._make_request(
            "/cgi-jstatus-E14303955"
        )  # Using your working Eddi serial

    def get_zappi_data(self) -> Dict:
        """Fetch data from Zappi device"""
        return self._make_request(
            "/cgi-jstatus-Z16186743"
        )  # Using your working Zappi serial

    def get_all_devices(self) -> Dict:
        """Fetch data from all devices"""
        return self._make_request("/cgi-jstatus-*")

    # Control methods from documentation
    def set_zappi_mode(
        self,
        zappi_serial: str,
        mode: int,
        boost_mode: int = 0,
        kwh: int = 0,
        complete_time: str = "0000",
    ) -> Dict:
        """Set Zappi charging mode

        Args:
            zappi_serial: Zappi device serial number
            mode: 1=Fast, 2=Eco, 3=Eco+, 4=Stop
            boost_mode: 0=None, 10=Manual, 11=Smart
            kwh: Amount of kWh to add for boost
            complete_time: Time to complete by for smart boost (HHMM format)
        """
        endpoint = (
            f"/cgi-zappi-mode-Z{zappi_serial}-{mode}-{boost_mode}-{kwh}-{complete_time}"
        )
        return self._make_request(endpoint)

    def set_eddi_boost(
        self, eddi_serial: str, boost_mode: int, heater: int, minutes: int
    ) -> Dict:
        """Set Eddi boost mode

        Args:
            eddi_serial: Eddi device serial number
            boost_mode: 10=Start Manual Boost
            heater: 1/2 for heater number, 11/12 for Relay 1/2
            minutes: Duration in minutes (0 to cancel)
        """
        endpoint = f"/cgi-eddi-boost-E{eddi_serial}-{boost_mode}-{heater}-{minutes}"
        return self._make_request(endpoint)
