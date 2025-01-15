//Map
const map = L.map('map').setView([52.1, 5.50], 7);

//Basemap
var osmUrl = 'https://a.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}@2x.png';
var osmAttrib = 'Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL';
var osm = L.tileLayer(osmUrl, {
    minZoom: 1,
    maxZoom: 24,
    attribution: osmAttrib
}).addTo(map);

//DTBmap
var dtbUrl = "https://geo.rijkswaterstaat.nl/arcgis/rest/services/GDR/dtb/MapServer";
var dtbLayer = L.esri.dynamicMapLayer({
	url: dtbUrl,
	layers: [0,1,3],
    minZoom: 17,
    maxZoom: 24
}).addTo(map);

// Function to style features based on the STATUS attribute
function getFeatureStyle(feature) {
    const statusColors = {
        'Nieuw': 'green',
        'Verwijderd': 'red',
        'Veranderd Nieuw': 'blue',
        'Veranderd Oud': 'grey'
    };
    const fillColor = statusColors[feature.properties.STATUS] || 'transparent';
    return {
        color: fillColor,         // Border color (same as fill color)
        weight: 3,                // Set the weight of the border (thickness)
        opacity: 0.5,
        fillColor: fillColor,     // Fill color based on STATUS
        fillOpacity: 0.5          // Opacity of the fill color
    };
}

// Function to style point features
function pointToLayer(feature, latlng) {
    const statusColors = {
        'Nieuw': 'green',
        'Verwijderd': 'red',
        'Veranderd ': 'blue'
    };
    return L.circleMarker(latlng, {
        radius: 4,
        fillColor: statusColors[feature.properties.STATUS],
        color: '#000',
        weight: 1,
        opacity: 0.5,
        fillOpacity: 0.5
    });
}

//Stuff for eachfeature
function onEachFeature(feature, layer) {
    if (feature.properties && feature.properties.STATUS !== 'Veranderd') {
        var popupContent = "<b>DTB ID:</b> " + feature.properties.DTB_ID + "<br>" +
                           "<b>Object:</b> " + feature.properties.TYPE_OMSCHRIJVING + "<br>" +
                           "<b>Status:</b> " + feature.properties.STATUS + "<br>";

        var paneName = 'feature-' + feature.properties.TYPE_OMSCHRIJVING;
        if (!map.getPane(paneName)) {
            map.createPane(paneName); 
            map.getPane(paneName).style.zIndex = 500;
            console.log('Pane created: ' + paneName);
        } else {
            console.log('Pane already exists: ' + paneName);
        }
        layer.options.pane = paneName;
        layer.bindPopup(popupContent);

        // Add click event listener to each feature
        layer.on('click', function(e) {
            // Bring the clicked feature to the front
            e.target.bringToFront();
        });
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

