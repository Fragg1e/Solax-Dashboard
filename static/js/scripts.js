// Update intervals (MyEnergi updates every 10 seconds, Solax every 5 mins)
const MYENERGI_UPDATE_INTERVAL = 10000;
const SOLAX_UPDATE_INTERVAL = 300000;

// Function to format numbers
function formatNumber(number, decimals = 2) {
  return Number(number).toFixed(decimals);
}

// Function to safely update element text content
function safelyUpdateElement(elementId, value) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = value;
    return true;
  }
  return false;
}

// Function to update the last update time
function updateLastUpdateTime() {
  const now = new Date();
  const timeString = now.toLocaleTimeString();
  safelyUpdateElement("lastUpdate", `Last updated: ${timeString}`);
}

// Function to show loading overlay
function showLoading() {
  const overlay = document.querySelector(".loading-overlay");
  if (overlay) {
    overlay.style.display = "flex";
  }
}

// Function to hide loading overlay
function hideLoading() {
  const overlay = document.querySelector(".loading-overlay");
  if (overlay) {
    overlay.style.display = "none";
  }
}

// Function to update battery level
function updateBatteryLevel(percentage) {
  const batteryLevel = document.getElementById("batteryLevel");
  const batteryPercentage = document.getElementById("batteryPercentage");
  if (batteryLevel && batteryPercentage) {
    batteryLevel.style.width = `${percentage}%`;
    batteryPercentage.textContent = `${percentage}%`;
  }
}

// Function to update grid status icon using MyEnergi data
function updateGridStatusIcon(power, source = "myenergi") {
  const gridStatusIcon = document.getElementById("gridStatusIcon");
  if (gridStatusIcon) {
    const icon = gridStatusIcon.querySelector("i");
    if (icon) {
      // For MyEnergi, negative means exporting, positive means importing
      // For Solax, positive means exporting, negative means importing
      const isExporting = source === "myenergi" ? power < 0 : power > 0;

      icon.className = isExporting ? "fas fa-arrow-up" : "fas fa-arrow-down";
      gridStatusIcon.classList.toggle("exporting", isExporting);
    }
  }
}

// Function to fetch and update Solax data
async function updateSolaxData() {
  try {
    const response = await fetch("/api/solax/data");
    const data = await response.json();

    // Check if the response indicates success
    if (data.success === true && data.data) {
      const solaxData = data.data;

      // Update power values with proper units
      safelyUpdateElement(
        "acpower",
        solaxData.acpower
          ? `${formatNumber(solaxData.acpower / 1000)} kW`
          : "N/A"
      );
      safelyUpdateElement(
        "yieldtoday",
        solaxData.yieldtoday
          ? `${formatNumber(solaxData.yieldtoday)} kWh`
          : "N/A"
      );
      safelyUpdateElement(
        "feedinpower",
        solaxData.feedinpower
          ? `${formatNumber(solaxData.feedinpower / 1000)} kW`
          : "N/A"
      );
      safelyUpdateElement(
        "feedinenergy",
        solaxData.feedinenergy
          ? `${formatNumber(solaxData.feedinenergy)} kWh`
          : "N/A"
      );
      safelyUpdateElement(
        "consumeenergy",
        solaxData.consumeenergy
          ? `${formatNumber(solaxData.consumeenergy)} kWh`
          : "N/A"
      );

      // Update battery information if available
      if (solaxData.batStatus !== undefined && solaxData.soc !== undefined) {
        updateBatteryLevel(solaxData.soc);
        safelyUpdateElement(
          "battery-status",
          solaxData.batStatus === 1 ? "Charging" : "Discharging"
        );
        safelyUpdateElement(
          "battery-power",
          solaxData.batPower
            ? `${formatNumber(solaxData.batPower / 1000)} kW`
            : "N/A"
        );
      }

      // Update grid status
      updateGridStatusIcon(solaxData.feedinpower);
    } else if (data.exception && data.exception.includes("Query success")) {
      // This is actually a success case with a misleading exception message
      // We don't have data to display, so show N/A
      safelyUpdateElement("acpower", "N/A");
      safelyUpdateElement("yieldtoday", "N/A");
      safelyUpdateElement("feedinpower", "N/A");
      safelyUpdateElement("feedinenergy", "N/A");
      safelyUpdateElement("consumeenergy", "N/A");
      safelyUpdateElement("battery-status", "N/A");
      safelyUpdateElement("battery-power", "N/A");
      updateBatteryLevel(0);
    } else {
      // Update UI to show error state
      safelyUpdateElement("acpower", "Error");
      safelyUpdateElement("yieldtoday", "Error");
      safelyUpdateElement("feedinpower", "Error");
      safelyUpdateElement("feedinenergy", "Error");
      safelyUpdateElement("consumeenergy", "Error");
      safelyUpdateElement("battery-status", "Error");
      safelyUpdateElement("battery-power", "Error");
      updateBatteryLevel(0);
    }
  } catch (error) {
    // Update UI to show error state
    safelyUpdateElement("acpower", "Error");
    safelyUpdateElement("yieldtoday", "Error");
    safelyUpdateElement("feedinpower", "Error");
    safelyUpdateElement("feedinenergy", "Error");
    safelyUpdateElement("consumeenergy", "Error");
    safelyUpdateElement("battery-status", "Error");
    safelyUpdateElement("battery-power", "Error");
    updateBatteryLevel(0);
  }
}

// Function to fetch and update MyEnergi data
async function updateMyEnergiData() {
  try {
    const response = await fetch("/api/myenergi/data");
    const data = await response.json();

    if (data.success) {
      // Update Eddi data if available
      if (data.eddi) {
        safelyUpdateElement("eddi-charge-rate", data.eddi.charge_rate);
        safelyUpdateElement("eddi-green-amount", data.eddi.green_amount_today);
        safelyUpdateElement("eddi-import-power", data.eddi.import_power);
        safelyUpdateElement("eddi-grid-power", data.eddi.grid_power);
        safelyUpdateElement("eddi-status", getEddiStatus(data.eddi.status));
        safelyUpdateElement("eddi-time", data.eddi.time);
      }

      // Update Zappi data if available
      if (data.zappi) {
        safelyUpdateElement("zappi-charge-speed", data.zappi.charge_speed);
        safelyUpdateElement("zappi-charge-rate", data.zappi.charge_rate);
        safelyUpdateElement("zappi-mode", getZappiMode(data.zappi.mode));
        safelyUpdateElement("zappi-status", getZappiStatus(data.zappi.status));
        safelyUpdateElement("zappi-charge-session", `${data.zappi.che} kWh`);
        safelyUpdateElement("zappi-phase", data.zappi.phase);
        safelyUpdateElement("zappi-time", data.zappi.time);

        // Calculate and update KMs
        const kms = (parseFloat(data.zappi.che) || 0) * 5;
        safelyUpdateElement("zappi-kms", `${kms.toFixed(1)} km`);
      }
    }
  } catch (error) {
    // Handle error silently
  }
}

// Helper function to update element values
function updateElementValue(elementId, value) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = value !== undefined && value !== null ? value : "N/A";
  }
}

// Helper function to convert Eddi status code to text
function getEddiStatus(statusCode) {
  const statusMap = {
    0: "Off",
    1: "On",
    2: "Heating",
    3: "Diverting",
    4: "Boosting",
    5: "Complete",
    6: "Error",
    7: "Locked",
    8: "Scheduled",
    9: "Waiting",
    10: "Ready",
    11: "Heating",
    12: "Diverting",
    13: "Boosting",
    14: "Complete",
    15: "Error",
  };
  return statusMap[statusCode] || `Unknown (${statusCode})`;
}

// Helper function to convert Zappi mode code to text
function getZappiMode(modeCode) {
  const modeMap = {
    1: "Fast",
    2: "Eco",
    3: "Eco+",
    4: "Stop",
    5: "Manual",
    6: "Schedule",
    7: "Locked",
    8: "Waiting",
    9: "Ready",
    10: "Charging",
    11: "Complete",
    12: "Error",
  };
  return modeMap[modeCode] || `Unknown (${modeCode})`;
}

// Helper function to convert Zappi status code to text
function getZappiStatus(statusCode) {
  const statusMap = {
    0: "Disconnected",
    1: "Connected",
    2: "Waiting",
    3: "Charging",
    4: "Complete",
    5: "Error",
    6: "Locked",
    7: "Scheduled",
    8: "Waiting",
    9: "Ready",
    10: "Charging",
    11: "Complete",
    12: "Error",
  };
  return statusMap[statusCode] || `Unknown (${statusCode})`;
}

// Helper function to convert Zappi phase setting to text
function getZappiPhase(phaseCode) {
  const phaseMap = {
    A: "Single Phase",
    B: "Three Phase",
    C: "Three Phase",
    D: "Three Phase",
  };
  return phaseMap[phaseCode] || `Unknown (${phaseCode})`;
}

// Function to start periodic updates
function updateAllData() {
  // Initial updates
  updateSolaxData();
  updateMyEnergiData();

  // Set up different intervals for MyEnergi and Solax
  setInterval(updateMyEnergiData, MYENERGI_UPDATE_INTERVAL);
  setInterval(updateSolaxData, SOLAX_UPDATE_INTERVAL);
}

// Initial update
updateAllData();
