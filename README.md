# Solar Dashboard

A web application that displays real-time data from Solax inverter and MyEnergi devices (Eddi and Zappi).

## Features

- Real-time solar panel data from Solax inverter
- MyEnergi device status (Eddi and Zappi)
- Grid import/export monitoring
- Battery status tracking
- Responsive dashboard design

## Local Development

1. Clone the repository:

```bash
git clone https://github.com/Fragg1e/Solax-Dashboard.git
cd Solax-Dashboard
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file with your credentials:

```
SOLAX_INVERTER_IP=your_inverter_ip
MYENERGI_HUB_SN=your_hub_serial_number
MYENERGI_API_KEY=your_api_key
```

4. Run the application:

```bash
python app.py
```

The application will be available at http://localhost:5000

## Deployment to Render

1. Fork this repository to your GitHub account

2. Create a new Web Service on Render:

   - Connect your GitHub repository
   - Select the repository
   - Choose "Python" as the environment
   - The build command will be: `pip install -r requirements.txt`
   - The start command will be: `gunicorn app:app`

3. Add the following environment variables in Render:

   - `SOLAX_INVERTER_IP`: Your Solax inverter IP address
   - `MYENERGI_HUB_SN`: Your MyEnergi hub serial number
   - `MYENERGI_API_KEY`: Your MyEnergi API key

4. Click "Create Web Service"

Render will automatically deploy your application and provide you with a URL.

## Environment Variables

- `SOLAX_INVERTER_IP`: IP address of your Solax inverter
- `MYENERGI_HUB_SN`: Serial number of your MyEnergi hub
- `MYENERGI_API_KEY`: API key for MyEnergi authentication

## License

MIT License
