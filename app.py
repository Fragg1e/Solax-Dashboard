from flask import Flask, render_template, request, jsonify, Response
import os
import requests
from dotenv import load_dotenv
import logging
import hashlib
import time
import urllib.parse
import json
from myenergi_api import MyEnergiAPI
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Reduce logging from other modules
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

app = Flask(__name__)
load_dotenv()

# Solax API configuration
SOLAX_API_URL = "https://www.solaxcloud.com:9443/proxy/api/getRealtimeInfo.do"
SOLAX_TOKEN_ID = os.getenv("SOLAX_TOKEN_ID")
SOLAX_WIFI_SN = os.getenv("SOLAX_WIFI_SN")

# MyEnergi API configuration
MYENERGI_HUB_SN = os.getenv("MYENERGI_HUB_SN")
MYENERGI_PASSWORD = os.getenv("MYENERGI_API_KEY")  # Using MYENERGI_API_KEY from .env

# OpenWeatherMap configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_CITY = os.getenv("OPENWEATHER_CITY", "London,UK")

# Initialize MyEnergi API client
myenergi_client = MyEnergiAPI(MYENERGI_HUB_SN, MYENERGI_PASSWORD)


def fetch_with_digest_auth(url, method, username, password):
    """Implement digest authentication for MyEnergi API"""
    try:
        # Initial request to get the WWW-Authenticate header
        response = requests.request(method, url)
        logger.info(f"Initial response status: {response.status_code}")

        if response.status_code == 401:
            www_auth = response.headers.get("www-authenticate", "")
            logger.info(f"WWW-Authenticate header: {www_auth}")

            if not www_auth:
                logger.error("No WWW-Authenticate header found")
                return None

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

            logger.info(f"Parsed auth parts: {auth_parts}")

            realm = auth_parts.get("realm", "")
            nonce = auth_parts.get("nonce", "")
            qop = (
                auth_parts.get("qop", "").split(",")[0] if "qop" in auth_parts else None
            )

            if not realm or not nonce:
                logger.error(f"Missing realm or nonce. Realm: {realm}, Nonce: {nonce}")
                return None

            # Generate cnonce (client nonce)
            cnonce = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
            nc = "00000001"  # nonce count
            uri = urllib.parse.urlparse(url).path

            # Calculate HA1 = MD5(username:realm:password)
            ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
            logger.info(f"HA1: {ha1}")

            # Calculate HA2 = MD5(method:uri)
            ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
            logger.info(f"HA2: {ha2}")

            # Calculate response
            if qop:
                response_hash = hashlib.md5(
                    f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
                ).hexdigest()
            else:
                response_hash = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

            logger.info(f"Response hash: {response_hash}")

            # Build Authorization header
            auth_header = [
                f'Digest username="{username}"',
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

            auth_header.append(f'response="{response_hash}"')

            final_header = ", ".join(auth_header)
            logger.info(f"Final Authorization header: {final_header}")

            # Make the actual request with the Authorization header
            return requests.request(
                method, url, headers={"Authorization": final_header}
            )

        return response
    except Exception as e:
        logger.error(f"Error in fetch_with_digest_auth: {str(e)}")
        return None


def get_solax_data():
    """Fetch data from Solax API"""
    # Prepare the request parameters
    params = {"tokenId": SOLAX_TOKEN_ID, "sn": SOLAX_WIFI_SN}

    # Make the request
    response = requests.get(SOLAX_API_URL, params=params)
    data = response.json()

    # Return the data directly
    return data


def get_myenergi_data():
    """Fetch data from MyEnergi devices"""
    try:
        # Get data from all devices
        all_devices = myenergi_client.get_all_devices()
        logger.info("MyEnergi API Response - All Devices: %s", all_devices)

        if not all_devices["success"]:
            return {"success": False, "error": all_devices["error"]}

        # Get specific device data
        eddi_response = myenergi_client.get_eddi_data()
        zappi_response = myenergi_client.get_zappi_data()

        logger.info("MyEnergi API Response - Eddi: %s", eddi_response)
        logger.info("MyEnergi API Response - Zappi: %s", zappi_response)

        # Extract device data from responses
        eddi_data = {}
        if eddi_response.get("success") and eddi_response.get("data"):
            eddi_list = eddi_response["data"].get("eddi", [])
            if eddi_list:
                eddi = eddi_list[0]  # Get the first Eddi device
                eddi_data = {
                    "charge_rate": f"{eddi.get('che', 0)} kWh",
                    "green_amount_today": f"{eddi.get('gen', 0)} W",
                    "import_power": f"{eddi.get('grd', 0)} W",
                    "grid_power": f"{eddi.get('ectp1', 0)} W",
                    "status": eddi.get("sta", 0),
                    "time": f"{eddi.get('tim', '')} {eddi.get('dat', '')}",
                }

        zappi_data = {}
        if zappi_response.get("success") and zappi_response.get("data"):
            zappi_list = zappi_response["data"].get("zappi", [])
            if zappi_list:
                zappi = zappi_list[0]  # Get the first Zappi device
                zappi_data = {
                    "charge_speed": f"{zappi.get('div', 0)} W",
                    "charge_rate": f"{zappi.get('che', 0)} kWh",
                    "mode": zappi.get("zmo", 0),
                    "status": zappi.get("pst", 0),
                    "che": zappi.get("che", 0),  # Charge session energy
                    "phase": zappi.get("pha", "N/A"),
                    "time": f"{zappi.get('tim', '')} {zappi.get('dat', '')}",
                }

        return {
            "success": True,
            "all_devices": all_devices.get("data", {}),
            "eddi": eddi_data,
            "zappi": zappi_data,
        }
    except Exception as e:
        logger.error("MyEnergi API Error: %s", str(e))
        return {"success": False, "error": str(e)}


@app.before_request
def log_request_info():
    """Log request information"""
    # Only log essential information
    logger.info(f"Path: {request.path}")
    logger.info(f"Method: {request.method}")


@app.after_request
def log_response_info(response):
    """Log response information"""
    # Only log essential information
    logger.info(f"Response status: {response.status_code}")
    return response


@app.route("/")
def index():
    """Main dashboard route"""
    solax_data = get_solax_data()
    myenergi_data = get_myenergi_data()
    return render_template(
        "index.html", solax_data=solax_data, myenergi_data=myenergi_data
    )


@app.route("/api/solax/data")
def solax_data():
    """API endpoint for Solax data"""
    return jsonify(get_solax_data())


@app.route("/api/myenergi/data")
def myenergi_data():
    """API endpoint for MyEnergi data"""
    return jsonify(get_myenergi_data())


@app.route("/weather")
def weather():
    """Weather forecast route"""
    current_weather = get_current_weather()
    forecast = get_weather_forecast()

    if current_weather is None:
        return render_template(
            "weather.html",
            error="Failed to fetch current weather data",
            city=OPENWEATHER_CITY,
        )

    if forecast is None:
        return render_template(
            "weather.html", error="Failed to fetch forecast data", city=OPENWEATHER_CITY
        )

    return render_template(
        "weather.html",
        current=current_weather,
        forecast=forecast,
        city=OPENWEATHER_CITY,
    )


@app.route("/api/weather/current")
def weather_current():
    """API endpoint for current weather"""
    current_weather = get_current_weather()
    if current_weather is None:
        return jsonify({"success": False, "error": "Failed to fetch weather data"})
    return jsonify({"success": True, "data": current_weather})


@app.route("/api/weather/forecast")
def weather_forecast():
    """API endpoint for weather forecast"""
    forecast = get_weather_forecast()
    if forecast is None:
        return jsonify({"success": False, "error": "Failed to fetch forecast data"})
    return jsonify({"success": True, "data": forecast})


def get_current_weather():
    """Get current weather data from OpenWeatherMap API"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={OPENWEATHER_CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()  # Return the raw API response
        else:
            return None
    except Exception as e:
        logger.error(f"Error fetching current weather: {str(e)}")
        return None


def get_weather_forecast():
    """Get 5-day weather forecast from OpenWeatherMap API"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={OPENWEATHER_CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Process forecast data to group by day
            daily_forecasts = {}
            for item in data["list"]:
                date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
                if date not in daily_forecasts:
                    daily_forecasts[date] = {
                        "temp_min": item["main"]["temp_min"],
                        "temp_max": item["main"]["temp_max"],
                        "description": item["weather"][0]["description"],
                        "icon": item["weather"][0]["icon"],
                        "humidity": item["main"]["humidity"],
                        "wind_speed": item["wind"]["speed"],
                    }
                else:
                    daily_forecasts[date]["temp_min"] = min(
                        daily_forecasts[date]["temp_min"], item["main"]["temp_min"]
                    )
                    daily_forecasts[date]["temp_max"] = max(
                        daily_forecasts[date]["temp_max"], item["main"]["temp_max"]
                    )
            return daily_forecasts
        else:
            return None
    except Exception as e:
        logger.error(f"Error fetching weather forecast: {str(e)}")
        return None


if __name__ == "__main__":
    app.run(debug=True)
