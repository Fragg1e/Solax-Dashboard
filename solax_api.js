
function getSolaxData(createCard, checkInverterStatus, createChart) {
    // Make the API call and display the data on the page
    fetch('/api/solax-proxy')

    .then(response => response.json())
        .then(data => {
            console.log(data);
            

            // Get the yieldtoday and feedinpower values from the data
            const yieldtoday = data.result.yieldtoday;
            const feedinpower = data.result.feedinpower;
            const powerdc1 = data.result.powerdc1;
            const powerdc2 = data.result.powerdc2;
            const batPower = data.result.batPower;
            const inverterStatus = data.result.inverterStatus;
            const soc = data.result.soc;
            const acpower = data.result.acpower;
            const yieldtotal = data.result.yieldtotal;
            const uploadTime = data.result.uploadTime;

            const currentTime = new Date();
            window.uploadTimeDate = new Date(currentTime.getTime() + 5 * 60 * 1000);

            const yieldtodayElement = document.getElementById("yield-today");
            yieldtodayElement.innerHTML = createCard("Yield Today", `${yieldtoday}KW`, );

            const co2SavedTodayElement = document.getElementById("co2-saved-today");
            co2SavedTodayElement.innerHTML = createCard("CO2 Saved Today", `${((yieldtoday)*0.345).toFixed(2)}Kg`);

            const moneySavedTodayElement = document.getElementById("money-saved-today");
            moneySavedTodayElement.innerHTML = createCard("Money Saved Today", `€${((yieldtoday)*0.3895).toFixed(2)}`);

            const yieldtotalElement = document.getElementById("yield-total");
            yieldtotalElement.innerHTML = createCard("Yield Total", `${(yieldtotal / 1000).toFixed(2)}MW`);

            

            const co2SavedTotalElement = document.getElementById("co2-saved-total");
            co2SavedTotalElement.innerHTML = createCard("CO2 saved Total", `${((yieldtotal)*0.345).toFixed(2)}Kg`);

            const moneySavedTotalElement = document.getElementById("money-saved-total");
            moneySavedTotalElement.innerHTML = createCard("Money Saved Total", `€${((yieldtotal)*0.3895).toFixed(2)}`);

            const feedinpowerElement = document.getElementById("feed-in-power");
            feedinpowerElement.innerHTML = createCard("Feed in Power", `${((feedinpower / 1000)).toFixed(2)}KW`);

            const solarpowerElement = document.getElementById("solar-power");
            solarpowerElement.innerHTML = createCard("Solar Power", `${((powerdc1 + powerdc2) / 1000).toFixed(2)}KW`);

            createChart(['Grid', 'Solar'], [((Math.abs(feedinpower) / 1000)).toFixed(2), ((powerdc1 + powerdc2) / 1000).toFixed(2)]);

            const batPowerElement = document.getElementById("bat-power");
            batPowerElement.innerHTML = createCard("Battery Power", `${((batPower / 1000)).toFixed(2)}KW`);

            const socElement = document.getElementById("state-of-charge");
            socElement.innerHTML = createCard("State of Charge", `${soc}%`, soc);

            const inverterStatusElement = document.getElementById("inverter-status");
            inverterStatusElement.innerHTML = createCard("Inverter Status", checkInverterStatus(inverterStatus));

            const acpowerElement = document.getElementById("ac-power");
            acpowerElement.innerHTML = createCard("AC Power", `${(acpower/1000).toFixed(2)}KW`);

            const houseloadElement = document.getElementById("house-load");
            houseloadElement.innerHTML = createCard("House Load", `${(((feedinpower * -1) + acpower)/1000).toFixed(2)}KW`);

            const uploadTimeElement = document.getElementById("last-upload");
            uploadTimeElement.innerHTML = createCard("Last Upload", `${uploadTime.slice(11,)}`);

        })
        .catch(error => console.log('error', error));
}

export default getSolaxData;