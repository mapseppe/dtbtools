function downloadGeojson(geojsonData) {
    // Convert the geojson data to a string
    const geojsonString = JSON.stringify(geojsonData, null, 2);

    // Create a Blob object containing the GeoJSON data
    const blob = new Blob([geojsonString], { type: 'application/geo+json' });

    // Create an anchor tag to trigger the download
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'data.geojson'; // The file name for download

    // Append the link to the DOM, click it, and then remove it
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}