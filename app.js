//Define express framework and ejs and routes
const express = require('express');
const path = require('path');
const app = express();
const geojsonRoutes = require('./routes/geojson');

//Set EJS engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

//Serve static files
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true}));

//Routes
app.use(geojsonRoutes);

//Homepage
app.get('/', (req, res) => {
    res.render('index');
});

//Verschilkaart Page
app.get('/dtbverschilkaart', (req, res) => {
    res.render('dtbverschilkaart');
});

app.get('/dtbverschilkaart/create', (req, res) => {
    res.render('createkaart', {resultMessage: "", resultLink: ""});
});

//404 error page
app.use((req, res) => {
    res.status(404).render('404');
});

//Activate server
app.listen(3000);