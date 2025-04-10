# Solax Energy Dashboard

A web application for monitoring and controlling Solax solar panel systems, batteries, inverters, and electric vehicles.

## Features

- Real-time monitoring of solar panel performance
- Battery status and management
- Inverter efficiency tracking
- Electric vehicle integration
- Weather-based solar power prediction
- Historical data visualization
- Data export functionality

## Technologies Used

- Flask (Python web framework)
- SQLAlchemy (Database ORM)
- Chart.js (Data visualization)
- OpenWeatherMap API (Weather data)
- Solax API (Solar system data)

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with the following variables:
   ```
   SOLAX_TOKEN_ID=your_token_id
   SOLAX_WIFI_SN=your_wifi_sn
   WEATHER_API_KEY=your_weather_api_key
   FLASK_APP=app.py
   FLASK_ENV=development
   DATABASE_URL=sqlite:///solax_data.db
   ```
4. Run the application: `python app.py`

## Deployment

This application is configured for deployment on Render. The `render.yaml` file contains the necessary configuration.

## License

MIT 