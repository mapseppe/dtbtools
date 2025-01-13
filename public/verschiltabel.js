function generateGeojsonTable(geojson) {
    const tableContainer = document.getElementById("geojson-table");
    tableContainer.innerHTML = ""; // Clear existing table if any

    if (!geojson || !geojson.features || geojson.features.length === 0) {
        tableContainer.innerHTML = "<p>No features available</p>";
        return;
    }

    // Define the specific fields to display
    const fieldsToDisplay = ['TYPE_OMSCHRIJVING', 'STATUS', 'DTB_ID'];

    // Define valid statuses to filter by
    const validStatuses = ['Nieuw', 'Verwijderd', 'Veranderd'];

    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const tbody = document.createElement("tbody");

    // Create the table headers
    const headerRow = document.createElement("tr");
    fieldsToDisplay.forEach(field => {
        const th = document.createElement("th");
        th.textContent = field;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Loop through each feature and add it to the table if STATUS is valid
    geojson.features.forEach(feature => {
        if (validStatuses.includes(feature.properties.STATUS)) {
            const row = document.createElement("tr");
            fieldsToDisplay.forEach(field => {
                const td = document.createElement("td");
                td.textContent = feature.properties[field] || "N/A"; // Show "N/A" if the property is missing
                row.appendChild(td);
            });
            tbody.appendChild(row);
        }
    });

    table.appendChild(tbody);
    tableContainer.appendChild(table);
}
