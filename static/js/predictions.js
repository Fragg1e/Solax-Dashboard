// Global variables
let predictionChart = null;
let weatherForecast = null;

// DOM Elements
const loadingOverlay = document.getElementById("loading-overlay");
const predictionForm = document.getElementById("prediction-form");
const predictionDays = document.getElementById("prediction-days");
const weatherForecastDiv = document.getElementById("weather-forecast");
const expectedGeneration = document.getElementById("expected-generation");
const potentialSavings = document.getElementById("potential-savings");
const confidenceLevel = document.getElementById("confidence-level");

// Initialize the page
document.addEventListener("DOMContentLoaded", () => {
  // Set up event listeners
  predictionForm.addEventListener("submit", handlePredictionSubmit);

  // Load initial data
  loadWeatherForecast();
});

// Handle prediction form submission
async function handlePredictionSubmit(event) {
  event.preventDefault();
  showLoading();

  try {
    const days = parseInt(predictionDays.value);
    await generatePrediction(days);
  } catch (error) {
    console.error("Error generating prediction:", error);
    showError("Failed to generate prediction. Please try again.");
  } finally {
    hideLoading();
  }
}

// Generate prediction for specified number of days
async function generatePrediction(days) {
  try {
    const response = await fetch(`/api/predictions?days=${days}`);
    if (!response.ok) throw new Error("Failed to fetch prediction data");

    const data = await response.json();
    updatePredictionDisplay(data);
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
}

// Update prediction display with new data
function updatePredictionDisplay(data) {
  // Update statistics
  expectedGeneration.querySelector(
    "span"
  ).textContent = `${data.total_generation.toFixed(1)} kWh`;
  potentialSavings.querySelector(
    "span"
  ).textContent = `€${data.total_savings.toFixed(2)}`;
  confidenceLevel.querySelector(
    "span"
  ).textContent = `${data.confidence_level}%`;

  // Update chart
  updatePredictionChart(data.daily_predictions);
}

// Update prediction chart
function updatePredictionChart(predictions) {
  const ctx = document.getElementById("prediction-chart").getContext("2d");

  // Destroy existing chart if it exists
  if (predictionChart) {
    predictionChart.destroy();
  }

  // Create new chart
  predictionChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: predictions.map((p) => p.date),
      datasets: [
        {
          label: "Predicted Generation (kWh)",
          data: predictions.map((p) => p.generation),
          borderColor: "#ffc107",
          backgroundColor: "rgba(255, 193, 7, 0.1)",
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: "Predicted Solar Generation",
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Generation (kWh)",
          },
        },
      },
    },
  });
}

// Load weather forecast
async function loadWeatherForecast() {
  try {
    const response = await fetch("/api/weather-forecast");
    if (!response.ok) throw new Error("Failed to fetch weather forecast");

    const data = await response.json();
    updateWeatherForecast(data);
  } catch (error) {
    console.error("Error loading weather forecast:", error);
    weatherForecastDiv.innerHTML =
      '<p class="text-danger">Failed to load weather forecast</p>';
  }
}

// Update weather forecast display
function updateWeatherForecast(data) {
  const forecastHtml = data.daily
    .map(
      (day) => `
        <div class="weather-day">
            <div class="date">${day.date}</div>
            <div class="temperature">${day.temperature}°C</div>
            <div class="conditions">${day.conditions}</div>
        </div>
    `
    )
    .join("");

  weatherForecastDiv.innerHTML = forecastHtml;
}

// Show loading overlay
function showLoading() {
  loadingOverlay.style.display = "flex";
}

// Hide loading overlay
function hideLoading() {
  loadingOverlay.style.display = "none";
}

// Show error message
function showError(message) {
  // You can implement this based on your UI needs
  alert(message);
}
