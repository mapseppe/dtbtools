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
var dtbUrl = "https://geo.rijkswaterstaat.nl/arcgis/rest/services/GDR/dtb/MapServer?sr=4326";
var dtbLayer = L.esri.dynamicMapLayer({
	url: dtbUrl,
	layers: [0,1,3],
    minZoom: 17,
    maxZoom: 24
}).addTo(map);

// Function to style polygon and line features
function getFeatureStyle(feature) {
    const statusColors = {
        'Nieuw': 'green',
        'Verwijderd': 'red',
        'Veranderd Nieuw': 'blue',
        'Veranderd Oud': 'grey'
    };
    const fillColor = statusColors[feature.properties.STATUS] || 'transparent';
    if (feature.geometry.type === 'Polygon') {
        return {
            color: fillColor,
            weight: 1,
            opacity: 0.15,
            fillColor: fillColor,
            fillOpacity: 0.5
        };
    } else if (feature.geometry.type === 'LineString') {
        return {
            color: fillColor,
            weight: 3,
            opacity: 0.5,
            fillColor: 'transparent',
            fillOpacity: 0
        };
    }
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
        color: 'transparent',
        weight: 1,
        opacity: 0.5,
        fillOpacity: 0.5
    });
}

//Change MultiString/Polygon to just String/Polygon, to adapt to leaflet functioning.
function convertMultiGeometriesToSingle(input) {
    const features = input.features.map(feature => {
        //Only do valid geometries
        if (feature.geometry && feature.geometry.type) {
            //MultiPolygon to Polygon
            if (feature.geometry.type === 'MultiPolygon') {
                const polygons = feature.geometry.coordinates.map(coords => {
                    return {
                        type: 'Feature',
                        geometry: {type: 'Polygon', coordinates: coords},
                        properties: feature.properties
                    };
                });
                return polygons;
            //MultiLineString to LineString
            } else if (feature.geometry.type === 'MultiLineString') {
                const lines = feature.geometry.coordinates.map(coords => {
                    return {
                        type: 'Feature',
                        geometry: {type: 'LineString', coordinates: coords},
                        properties: feature.properties
                    };
                });
                return lines;
            //Keep other features the same
            } else {
                return feature;
            }
        //Report invalid geometries (shouldn't occur anymore, but used to do in earlier version)
        } else {
            console.warn('Feature without valid geometry:', feature);
            return [];
        }
    }).flat();
    return {
        type: 'FeatureCollection',
        features: features
    };
}

// Function to load GeoJSON, apply symbology, and zoom to the layer
function loadGeojson(input) {
    const geojsonData = convertMultiGeometriesToSingle(input);

    const points = geojsonData.features.filter(feature => feature.geometry.type === 'Point');
    const lines = geojsonData.features.filter(feature => feature.geometry.type === 'LineString');
    const polygons = geojsonData.features.filter(feature => feature.geometry.type === 'Polygon');

    //Index the layers so that the points are on top, then lines, then polygons below
    const polygonsLayer = L.geoJSON(polygons, {
        style: function(feature) {
            return getFeatureStyle(feature);
        },
        zIndex: 1,
    })
    const linesLayer = L.geoJSON(lines, {
        style: function(feature) {
            return getFeatureStyle(feature);
        },
        zIndex: 2,
    })
    const pointsLayer = L.geoJSON(points, {
        style: function(feature) {
            return getFeatureStyle(feature);
        },
        pointToLayer: pointToLayer,
        zIndex: 3,
    })
    const verschilkaartLayer = L.layerGroup([pointsLayer, linesLayer, polygonsLayer]);
    verschilkaartLayer.addTo(map);

    // Zoom to the bounds of the GeoJSON layer after it's added to the map
    let combinedBounds = pointsLayer.getBounds();
    combinedBounds.extend(linesLayer.getBounds());
    combinedBounds.extend(polygonsLayer.getBounds());
    map.fitBounds(combinedBounds);
	//Layer control in the top left for the selection/toggleability of layers
	var mapControl = {
		"Verschilkaart": verschilkaartLayer,
		"DTB": dtbLayer };
	var basmapControl = {
		"Achtergrondkaart": osm };
	var layerControl = L.control.layers(basmapControl, mapControl).addTo(map);
}

//Event on clicking
let lastMarker = null;
map.on('click', function(event) {
    const latlng = event.latlng;
    //Change the distance of how close the nearby objects should appear
    const proximityRadius = 1;
    if (lastMarker) {
        map.removeLayer(lastMarker);
    }
    checkProximity(latlng, proximityRadius);
    const plusIcon = L.divIcon({
        className: 'plus-icon',
        html: '+',
        iconAnchor: [17, 11]
    });
    lastMarker = L.marker(latlng, { icon: plusIcon }).addTo(map);
});

//Style of the click-cursor
const style = document.createElement('style');
style.innerHTML = `
    .plus-icon {
        font-size: 60px !important;
        color: black;
        text-align: center;
    }
`;
document.head.appendChild(style);

//Check which features are nearby the click
function checkProximity(latlng, radius) {
    const buffer = turf.buffer(turf.point([latlng.lng, latlng.lat]), radius, { units: 'meters' });
    const validFeatures = inputGeojson.features.filter(feature => 
        feature.geometry && feature.geometry.type
    );
    let intersectingFeatures = [];
    validFeatures.forEach(feature => {
        let featureGeometry = feature.geometry;
        if (turf.booleanIntersects(featureGeometry, buffer)) {
            intersectingFeatures.push(feature);
        }
    });
    showResults(intersectingFeatures);
}

//Return the results of nearby features of the clicked location in table-form
function showResults(features) {
    //Table base and link to html
    const tableContainer = document.getElementById('proximity-results-container');
    let html = '<table><tr><th>DTB ID</th><th>Object (oud)</th><th>Object (nieuw)</th><th>Status</th></tr>';
    //Dont add features with 'Veranderd' to viewing
    const filteredFeatures = features.filter(function(feature) {
        return feature.properties.STATUS !== 'Veranderd';
    });
    //If no features are found near cursor
    if (filteredFeatures.length === 0) {
        html += '<tr><td colspan="4">No features found with the selected status.</td></tr>';
    //Else list each feature that is found near cursor
    } else {
        filteredFeatures.forEach(function(feature) {
            html += `<tr>
                        <td>${feature.properties.DTB_ID || '-'}</td>
                        <td>${feature.properties.TYPE_oud || '-'}</td>
                        <td>${feature.properties.TYPE_nieuw || '-'}</td>
                        <td>${feature.properties.STATUS || '-'}</td>
                    </tr>`;
        });
    }
    //Final html-part of table
    html += '</table>';
    tableContainer.innerHTML = html;
}