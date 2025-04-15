// Global variables
let generationChart = null;
let gridChart = null;
let currentPeriod = 30; // Default to 30 days

// DOM Elements
const loadingOverlay = document.getElementById("loading-overlay");
const periodButtons = document.querySelectorAll("[data-period]");
const totalGeneration = document.getElementById("total-generation");
const avgDaily = document.getElementById("avg-daily");
const totalSavings = document.getElementById("total-savings");
const greenPercentage = document.getElementById("green-percentage");
const exportButton = document.getElementById("export-csv");

// Chart colors
const chartColors = {
  solar: "#FFB74D",
  grid: "#4FC3F7",
  feedIn: "#81C784",
  actual: "#4FC3F7",
  prediction: "#FFB74D",
};

// Common chart options
const chartOptions = {
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 2,
  scales: {
    x: {
      type: "time",
      time: {
        unit: "day",
        displayFormats: {
          day: "MMM d",
        },
      },
      title: {
        display: true,
        text: "Date",
      },
    },
    y: {
      beginAtZero: true,
      title: {
        display: true,
        text: "Value",
      },
    },
  },
  plugins: {
    legend: {
      position: "top",
    },
  },
};

// Function to fetch solar data from the API
async function fetchData(days = 30) {
  try {
    const response = await fetch(`/api/solar-data?days=${days}`);
    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || "Failed to fetch data");
    }

    return result.data;
  } catch (error) {
    throw error;
  }
}

// Function to update all charts with new data
function updateCharts(data) {
  updateFinancialChart(data);
  updateGenerationChart(data);
  updatePredictionChart(data);
}

// Function to update the financial benefits chart
function updateFinancialChart(data) {
  const canvas = document.getElementById("financial-chart");
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  // Safely destroy existing chart
  if (window.financialChart instanceof Chart) {
    window.financialChart.destroy();
  }

  const dates = data.map((d) => d.date);
  const savings = data.map((d) => d.grid_export * 0.15); // Assuming £0.15 per kWh export rate

  window.financialChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Daily Financial Benefits (£)",
          data: savings,
          borderColor: "rgb(75, 192, 192)",
          tension: 0.1,
          fill: false,
        },
      ],
    },
    options: {
      ...chartOptions,
      scales: {
        ...chartOptions.scales,
        y: {
          ...chartOptions.scales.y,
          title: {
            display: true,
            text: "Amount (£)",
          },
        },
      },
    },
  });
}

// Function to update the generation vs grid usage chart
function updateGenerationChart(data) {
  const canvas = document.getElementById("generation-chart");
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  // Safely destroy existing chart
  if (generationChart) {
    generationChart.destroy();
  }

  const dates = data.map((d) => d.date);
  const generation = data.map((d) => d.generation);
  const gridImport = data.map((d) => d.grid_import);
  const gridExport = data.map((d) => d.grid_export);

  generationChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Solar Generation",
          data: generation,
          borderColor: "rgb(255, 205, 86)",
          tension: 0.1,
          fill: false,
        },
        {
          label: "Grid Import",
          data: gridImport,
          borderColor: "rgb(255, 99, 132)",
          tension: 0.1,
          fill: false,
        },
        {
          label: "Grid Export",
          data: gridExport,
          borderColor: "rgb(75, 192, 192)",
          tension: 0.1,
          fill: false,
        },
      ],
    },
    options: {
      ...chartOptions,
      scales: {
        ...chartOptions.scales,
        y: {
          ...chartOptions.scales.y,
          title: {
            display: true,
            text: "Energy (kWh)",
          },
        },
      },
    },
  });
}

// Function to update the prediction chart
function updatePredictionChart(data) {
  const canvas = document.getElementById("prediction-chart");
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  // Safely destroy existing chart
  if (window.predictionChart instanceof Chart) {
    window.predictionChart.destroy();
  }

  // Get actual data for comparison
  const actualDates = data.map((d) => d.date);
  const actualGeneration = data.map((d) => d.generation);

  // Create the chart with proper options
  window.predictionChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: actualDates,
      datasets: [
        {
          label: "Actual Generation",
          data: actualGeneration,
          borderColor: "rgb(75, 192, 192)",
          tension: 0.1,
          fill: false,
        },
      ],
    },
    options: {
      ...chartOptions,
      scales: {
        ...chartOptions.scales,
        y: {
          ...chartOptions.scales.y,
          title: {
            display: true,
            text: "Energy (kWh)",
          },
        },
      },
    },
  });
}

// Function to export data to CSV
function exportToCSV(data) {
  const csvContent = [
    // CSV Header
    [
      "Date",
      "Generation (kWh)",
      "Grid Import (kWh)",
      "Grid Export (kWh)",
      "Battery Charge (kWh)",
      "Battery Discharge (kWh)",
    ].join(","),
    // CSV Data
    ...data.map((row) =>
      [
        row.date,
        row.generation,
        row.grid_import,
        row.grid_export,
        row.battery_charge,
        row.battery_discharge,
      ].join(",")
    ),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  link.setAttribute("href", url);
  link.setAttribute("download", "solar_data.csv");
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Function to load and display data
async function loadData(days) {
  try {
    // Show loading state
    document.querySelectorAll(".chart-container").forEach((container) => {
      container.style.opacity = "0.5";
    });

    const data = await fetchData(days);
    updateCharts(data);

    // Hide loading state
    document.querySelectorAll(".chart-container").forEach((container) => {
      container.style.opacity = "1";
    });

    // Store data for export
    window.currentData = data;
  } catch (error) {
    // Show error message to user
    document.querySelectorAll(".chart-container").forEach((container) => {
      container.style.opacity = "1";
      container.innerHTML =
        '<div class="alert alert-danger">Failed to load data. Please try again later.</div>';
    });
  }
}

// Initialize page
document.addEventListener("DOMContentLoaded", () => {
  // Set up event listeners
  periodButtons.forEach((button) => {
    button.addEventListener("click", () => handlePeriodChange(button));
  });
  exportButton.addEventListener("click", handleExport);

  // Load initial data
  loadAnalyticsData(currentPeriod);
});

// Handle period change
function handlePeriodChange(button) {
  // Update active state
  periodButtons.forEach((btn) => btn.classList.remove("active"));
  button.classList.add("active");

  // Update period and reload data
  currentPeriod = parseInt(button.dataset.period);
  loadAnalyticsData(currentPeriod);
}

// Load analytics data
async function loadAnalyticsData(days) {
  showLoading();

  try {
    // Fetch summary data
    const summaryResponse = await fetch(`/api/analytics/summary?days=${days}`);
    if (!summaryResponse.ok) throw new Error("Failed to fetch summary data");
    const summaryData = await summaryResponse.json();

    // Fetch detailed data
    const dataResponse = await fetch(`/api/solar-data?days=${days}`);
    if (!dataResponse.ok) throw new Error("Failed to fetch detailed data");
    const responseData = await dataResponse.json();

    // Check if the response has the expected format
    if (!responseData.success || !Array.isArray(responseData.data)) {
      throw new Error("Invalid data format received from server");
    }

    // Update display
    updateSummaryDisplay(summaryData);
    updateCharts(responseData.data);
  } catch (error) {
    showError("Failed to load analytics data. Please try again.");
  } finally {
    hideLoading();
  }
}

// Update summary display
function updateSummaryDisplay(data) {
  if (!data.success) {
    showError(data.error || "Failed to load summary data");
    return;
  }

  totalGeneration.querySelector(
    "span"
  ).textContent = `${data.total_generation} kWh`;
  avgDaily.querySelector("span").textContent = `${data.avg_daily} kWh`;
  totalSavings.querySelector("span").textContent = `€${data.total_savings}`;
  greenPercentage.querySelector(
    "span"
  ).textContent = `${data.green_percentage}%`;
}

// Update grid chart
function updateGridChart(data) {
  const canvas = document.getElementById("grid-chart");
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  // Safely destroy existing chart
  if (window.gridChart instanceof Chart) {
    window.gridChart.destroy();
  }

  const dates = data.map((d) => d.date);
  const gridImport = data.map((d) => d.grid_import);
  const gridExport = data.map((d) => d.grid_export);

  window.gridChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Grid Import",
          data: gridImport,
          borderColor: "rgb(255, 99, 132)",
          tension: 0.1,
          fill: false,
        },
        {
          label: "Grid Export",
          data: gridExport,
          borderColor: "rgb(75, 192, 192)",
          tension: 0.1,
          fill: false,
        },
      ],
    },
    options: {
      ...chartOptions,
      scales: {
        ...chartOptions.scales,
        y: {
          ...chartOptions.scales.y,
          title: {
            display: true,
            text: "Energy (kWh)",
          },
        },
      },
    },
  });
}

// Handle CSV export
async function handleExport() {
  try {
    const response = await fetch(
      `/api/solar-data/download?days=${currentPeriod}`
    );
    if (!response.ok) throw new Error("Failed to download data");

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `solar_data_${currentPeriod}days.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error("Error exporting data:", error);
    showError("Failed to export data. Please try again.");
  }
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
