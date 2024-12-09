//Map
const map = L.map('map').setView([52.1, 5.50], 7);

//Basemap
var osmUrl = 'https://a.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}@2x.png';
var osmAttrib = 'Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL';
var osm = L.tileLayer(osmUrl, {
    minZoom: 1,
    maxZoom: 20,
    attribution: osmAttrib
}).addTo(map);

//DTBmap
var dtbUrl = "https://geo.rijkswaterstaat.nl/arcgis/rest/services/GDR/dtb/MapServer";
var dtbLayer = L.esri.dynamicMapLayer({
	url: dtbUrl,
	layers: [0,1,3]
}).addTo(map);

// Function to style features based on the STATUS attribute
function getFeatureStyle(feature) {
    const statusColors = {
        'Nieuw': 'green',
        'Verwijderd': 'red',
        'Veranderd': 'blue'
    };
    return {
        color: statusColors[feature.properties.STATUS] || 'black', // Fallback color
        weight: feature.geometry.type === 'LineString' ? 3 : 1,
        fillColor: statusColors[feature.properties.STATUS] || 'blue',
        fillOpacity: 0.5
    };
}

// Function to style point features
function pointToLayer(feature, latlng) {
    const statusColors = {
        'Nieuw': 'green',
        'Verwijderd': 'red',
        'Veranderd': 'blue'
    };
    return L.circleMarker(latlng, {
        radius: 4,
        fillColor: statusColors[feature.properties.STATUS] || 'blue',
        color: '#000',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8
    });
}

//Stuff for eachfeature
function onEachFeature(feature, layer) {
	if (feature.properties) {
        var popupContent = "<b>DTB ID:</b> " + feature.properties.DTB_ID + "<br>" +
                           "<b>Object:</b> " + feature.properties.THEMA + "<br>" +
                           "<b>Status:</b> " + feature.properties.STATUS + "<br>";
        layer.bindPopup(popupContent);
	}
}

// Function to load GeoJSON, apply symbology, and zoom to the layer
function loadGeojson(input) {
    var geojsonLayer = L.geoJSON(input, {
        style: function(feature) {
            return getFeatureStyle(feature); // Apply style to polygons and lines
        },
        pointToLayer: function(feature, latlng) {
            return pointToLayer(feature, latlng); // Apply style to points
        },
		onEachFeature: onEachFeature
    }).addTo(map);

    // Zoom to the bounds of the GeoJSON layer after it's added to the map
    map.fitBounds(geojsonLayer.getBounds());
	//Layer control in the top left for the selection/toggleability of layers
	var mapControl = {
		"Verschilkaart": geojsonLayer,
		"DTB": dtbLayer };
	var basmapControl = {
		"Achtergrondkaart": osm };
	var layerControl = L.control.layers(basmapControl, mapControl).addTo(map);
}

