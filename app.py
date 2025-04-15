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
from database import (
    init_db,
    import_csv_data,
    get_all_data,
    get_recent_data,
    get_financial_summary,
)
from prediction import train_model, predict_next_days
import pandas as pd
import csv
from io import StringIO

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

# Initialize the database and import data
init_db()
import_csv_data("history_solar_data.csv")


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
    try:
        # Log the API configuration
        logger.info(f"Using Solax API URL: {SOLAX_API_URL}")
        logger.info(
            f"Token ID length: {len(SOLAX_TOKEN_ID) if SOLAX_TOKEN_ID else 'None'}"
        )
        logger.info(
            f"WiFi SN length: {len(SOLAX_WIFI_SN) if SOLAX_WIFI_SN else 'None'}"
        )

        # Prepare the request parameters
        params = {"tokenId": SOLAX_TOKEN_ID, "sn": SOLAX_WIFI_SN}

        # Log the full request URL with parameters
        full_url = f"{SOLAX_API_URL}?tokenId={SOLAX_TOKEN_ID}&sn={SOLAX_WIFI_SN}"
        logger.info(f"Full request URL: {full_url}")

        response = requests.get(SOLAX_API_URL, params=params)
        logger.info(f"Solax API response status: {response.status_code}")
        logger.info(f"Solax API response headers: {dict(response.headers)}")
        logger.info(f"Solax API raw response: {response.text}")

        if response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"Parsed Solax API response: {json.dumps(data, indent=2)}")

                # Check if the response indicates an error
                if isinstance(data, dict):
                    if data.get("success", False) is False:
                        error_msg = f"API returned error: {data.get('exception', 'Unknown error')}"
                        logger.error(error_msg)
                        return {"success": False, "exception": error_msg}

                    if "result" in data and isinstance(data["result"], dict):
                        result = data["result"]
                        transformed_data = {
                            "success": True,
                            "data": {
                                "acpower": result.get("acpower", 0),
                                "yieldtoday": result.get("yieldtoday", 0),
                                "feedinpower": result.get("feedinpower", 0),
                                "feedinenergy": result.get("feedinenergy", 0),
                                "consumeenergy": result.get("consumeenergy", 0),
                                "batStatus": result.get("batStatus", 0),
                                "soc": result.get("soc", 0),
                                "batPower": result.get("batPower", 0),
                            },
                        }
                        logger.info(
                            f"Transformed Solax data: {json.dumps(transformed_data, indent=2)}"
                        )
                        return transformed_data
                    else:
                        error_msg = f"Missing or invalid 'result' in response: {data}"
                        logger.error(error_msg)
                        return {"success": False, "exception": error_msg}
                else:
                    error_msg = f"Unexpected response type: {type(data)}"
                    logger.error(error_msg)
                    return {"success": False, "exception": error_msg}
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON response: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "exception": error_msg}
        else:
            error_msg = f"API Error: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            return {"success": False, "exception": error_msg}

    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "exception": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "exception": error_msg}


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
def get_solax_api_data():
    """API endpoint for Solax data"""
    data = get_solax_data()
    return jsonify(data)


@app.route("/api/myenergi/data")
def get_myenergi_api_data():
    """API endpoint for MyEnergi data"""
    data = get_myenergi_data()
    # Only log the success status and device counts
    if data.get("success"):
        eddi_count = len(data.get("data", {}).get("eddi", []))
        zappi_count = len(data.get("data", {}).get("zappi", []))
        logger.info(
            f"MyEnergi data retrieved successfully: {eddi_count} Eddi, {zappi_count} Zappi devices"
        )
    return jsonify(data)


# New routes for direct MyEnergi API access
@app.route("/api/myenergi/cgi-all")
def proxy_myenergi_all():
    """Proxy endpoint for MyEnergi cgi-all endpoint"""
    try:
        # Use the same endpoint as in the working implementation
        api_endpoint = "cgi-jstatus-*"
        url = f"https://s18.myenergi.net/{api_endpoint}"
        logger.info(f"Proxying request to: {url}")

        # Use the same authentication method as in the working implementation
        response = fetch_with_digest_auth(
            url, request.method, MYENERGI_HUB_SN, MYENERGI_PASSWORD
        )

        if response is None:
            logger.error("Failed to get response from MyEnergi API")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to get response from MyEnergi API",
                    }
                ),
                500,
            )

        logger.info(f"Response status: {response.status_code}")

        # Return the JSON response
        try:
            json_data = response.json()
            return jsonify(json_data), response.status_code
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {str(e)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Invalid JSON response: {str(e)}",
                        "response_text": response.text[:200],
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/zappi-proxy")
def proxy_zappi():
    """Proxy endpoint for Zappi device"""
    try:
        url = "https://s18.myenergi.net/cgi-jstatus-Z16186743"
        logger.info(f"Proxying Zappi request to: {url}")

        response = fetch_with_digest_auth(
            url, "GET", MYENERGI_HUB_SN, MYENERGI_PASSWORD
        )

        if response is None or not response.ok:
            logger.error(
                f"Failed to get Zappi data: {response.status_code if response else 'No response'}"
            )
            return jsonify({"success": False, "error": "Failed to get Zappi data"}), 500

        json_data = response.json()
        return jsonify(json_data), response.status_code

    except Exception as e:
        logger.error(f"Zappi proxy error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/eddi-proxy")
def proxy_eddi():
    """Proxy endpoint for Eddi device"""
    try:
        url = "https://s18.myenergi.net/cgi-jstatus-E14303955"
        logger.info(f"Proxying Eddi request to: {url}")

        response = fetch_with_digest_auth(
            url, "GET", MYENERGI_HUB_SN, MYENERGI_PASSWORD
        )

        if response is None or not response.ok:
            logger.error(
                f"Failed to get Eddi data: {response.status_code if response else 'No response'}"
            )
            return jsonify({"success": False, "error": "Failed to get Eddi data"}), 500

        json_data = response.json()
        return jsonify(json_data), response.status_code

    except Exception as e:
        logger.error(f"Eddi proxy error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/weather")
def weather():
    """Weather forecast page"""
    try:
        # Get current weather
        current_url = f"https://api.openweathermap.org/data/2.5/weather?q={OPENWEATHER_CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
        current_response = requests.get(current_url)
        current_data = current_response.json()

        # Get 5-day forecast
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={OPENWEATHER_CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
        forecast_response = requests.get(forecast_url)
        forecast_data = forecast_response.json()

        # Process forecast data to group by day
        daily_forecasts = {}
        if forecast_data.get("list"):
            for item in forecast_data["list"]:
                date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
                if date not in daily_forecasts:
                    daily_forecasts[date] = {
                        "temp_min": float("inf"),
                        "temp_max": float("-inf"),
                        "description": item["weather"][0]["description"],
                        "icon": item["weather"][0]["icon"],
                        "humidity": item["main"]["humidity"],
                        "wind_speed": item["wind"]["speed"],
                    }
                daily_forecasts[date]["temp_min"] = min(
                    daily_forecasts[date]["temp_min"], item["main"]["temp_min"]
                )
                daily_forecasts[date]["temp_max"] = max(
                    daily_forecasts[date]["temp_max"], item["main"]["temp_max"]
                )

        return render_template(
            "weather.html",
            current=current_data,
            forecast=daily_forecasts,
            city=OPENWEATHER_CITY,
        )
    except Exception as e:
        logger.error(f"Weather API Error: {str(e)}")
        return render_template("weather.html", error=str(e))


@app.route("/predictions")
def predictions():
    """Render the predictions page"""
    return render_template("predictions.html")


@app.route("/analytics")
def analytics():
    """Render the analytics page"""
    return render_template("analytics.html")


@app.route("/api/predictions")
def get_predictions():
    """Get solar generation predictions for the next N days"""
    try:
        days = int(request.args.get("days", 7))
        predictions = predict_next_days(days)

        # Calculate total generation and savings
        total_generation = sum(p["generation"] for p in predictions)
        total_savings = total_generation * 0.18  # 18 cents per kWh

        return jsonify(
            {
                "success": True,
                "total_generation": total_generation,
                "total_savings": total_savings,
                "confidence_level": 85,  # This could be calculated based on weather forecast accuracy
                "daily_predictions": predictions,
            }
        )
    except Exception as e:
        logger.error(f"Error generating predictions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analytics/summary")
def get_analytics_summary():
    """Get summary statistics for the analytics page"""
    try:
        days = int(request.args.get("days", 30))
        data = get_recent_data(days)

        if data.empty:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data available for the selected period",
                    }
                ),
                404,
            )

        # Calculate summary statistics and convert to standard Python types
        total_generation = float(data["generation"].fillna(0).sum())
        avg_daily = float(data["generation"].fillna(0).mean())
        total_savings = float(total_generation * 0.18)  # 18 cents per kWh

        # Handle division by zero and NaN values for green percentage
        generation = data["generation"].fillna(0)
        grid_import = data["grid_import"].fillna(0)
        total_energy = generation + grid_import
        green_percentage = float(
            ((generation / total_energy.replace(0, 1)) * 100).fillna(0).mean()
        )

        return jsonify(
            {
                "success": True,
                "total_generation": round(total_generation, 2),
                "avg_daily": round(avg_daily, 2),
                "total_savings": round(total_savings, 2),
                "green_percentage": round(green_percentage, 2),
            }
        )
    except Exception as e:
        logger.error(f"Error getting analytics summary: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/solar-data")
def get_solar_data():
    """
    Get historical solar data for a specified time period.
    Query parameters:
    - days (optional): Number of days of data to return (default: 30)
    Returns:
    - JSON object containing solar generation data
    """
    try:
        days = request.args.get("days", default=30, type=int)
        data = get_recent_data(days)

        if data is None or data.empty:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data available for the specified period",
                    }
                ),
                404,
            )

        # Convert DataFrame to list of dictionaries
        formatted_data = []
        for _, row in data.iterrows():
            formatted_data.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "generation": (
                        float(row["generation"]) if "generation" in row else 0
                    ),
                    "grid_import": (
                        float(row["grid_import"]) if "grid_import" in row else 0
                    ),
                    "grid_export": (
                        float(row["grid_export"]) if "grid_export" in row else 0
                    ),
                    "battery_charge": (
                        float(row["battery_charge"]) if "battery_charge" in row else 0
                    ),
                    "battery_discharge": (
                        float(row["battery_discharge"])
                        if "battery_discharge" in row
                        else 0
                    ),
                }
            )

        return jsonify({"success": True, "data": formatted_data})

    except Exception as e:
        logger.error(f"Error fetching solar data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/solar-data/download")
def download_solar_data():
    """Download solar data as CSV for the specified time period"""
    try:
        days = request.args.get("days", default=30, type=int)
        data = get_recent_data(days)

        if data.empty:
            return jsonify({"success": False, "error": "No data available"}), 404

        # Create a string buffer to write CSV data
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Date",
                "Solar Production (kWh)",
                "Grid Import (kWh)",
                "Feed-in (kWh)",
                "Battery Charge (kWh)",
                "Battery Discharge (kWh)",
                "Green Percentage (%)",
                "Money Saved ($)",
                "Feed-in Revenue ($)",
                "Total Benefit ($)",
            ]
        )

        # Write data rows
        for i in range(len(data)):
            generation = data["generation"].iloc[i]
            grid_import = data["grid_import"].iloc[i]
            grid_export = data["grid_export"].iloc[i]
            battery_charge = data["battery_charge"].iloc[i]
            battery_discharge = data["battery_discharge"].iloc[i]

            # Calculate financial metrics
            money_saved = generation * 0.18
            feed_in_revenue = grid_export * 0.18
            total_benefit = money_saved + feed_in_revenue

            # Calculate green percentage
            total_energy = generation + grid_import
            green_percentage = (
                (generation / total_energy * 100) if total_energy > 0 else 0
            )

            writer.writerow(
                [
                    data["date"].iloc[i].strftime("%Y-%m-%d"),
                    round(generation, 2),
                    round(grid_import, 2),
                    round(grid_export, 2),
                    round(battery_charge, 2),
                    round(battery_discharge, 2),
                    round(green_percentage, 2),
                    round(money_saved, 2),
                    round(feed_in_revenue, 2),
                    round(total_benefit, 2),
                ]
            )

        # Create the response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=solar_data_{days}days.csv"
            },
        )
    except Exception as e:
        logger.error(f"Error downloading solar data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/solax/test")
def test_solax_api():
    """Test endpoint for Solax API connection"""
    try:
        # Log environment variables
        logger.info("Environment variables:")
        logger.info(f"SOLAX_TOKEN_ID: {SOLAX_TOKEN_ID}")
        logger.info(f"SOLAX_WIFI_SN: {SOLAX_WIFI_SN}")

        # Prepare the request parameters
        params = {"tokenId": SOLAX_TOKEN_ID, "sn": SOLAX_WIFI_SN}

        # Make the request
        response = requests.get(SOLAX_API_URL, params=params)

        return jsonify(
            {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "text": response.text,
                "url": response.url,
                "env_vars": {"token_id": SOLAX_TOKEN_ID, "wifi_sn": SOLAX_WIFI_SN},
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": str(e),
                    "env_vars": {"token_id": SOLAX_TOKEN_ID, "wifi_sn": SOLAX_WIFI_SN},
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(debug=True)
