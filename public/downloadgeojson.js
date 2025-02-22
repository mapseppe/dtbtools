function downloadGeojson(geojsonData) {
    //Download geojson button
    const geojsonString = JSON.stringify(geojsonData, null, 2);
    const blob = new Blob([geojsonString], { type: 'application/geo+json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'data.geojson';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}