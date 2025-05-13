function openGoogleMaps() {
    //Open google maps locatie button
    if (!lastLatlng) {
        alert("Klik eerst een locatie op de kaart aan");
        return;
    }
    const latitude = lastLatlng.lat;
    const longitude = lastLatlng.lng;
    const googleMapsUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
    window.open(googleMapsUrl, '_blank');
}