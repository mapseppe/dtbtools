const express = require('express');
const fs = require('fs');
const path = require('path');
const router = express.Router();

////////////////////////////////////////
//      Load existing geojson file    //
////////////////////////////////////////
router.get('/dtbverschilkaart?:id', (req, res) => {
    const id = req.query.geojsonId; // Get the ID from the URL
    const geojsonPath = path.join(__dirname, '../data', `${id}.geojson`);

    //Check if geojson exists in databse
    if (id != undefined) {
    fs.readFile(geojsonPath, 'utf8', (err, data) => {
        if (err) {
            console.error("File Read Error:", err.message);
            return res.render('dtbverschilkaart', { resultMessage: "Geen kaart gevonden met ID: " + id, resultGeojson: ""});
        }
        //Respond geojson
        try {
            const geojsonData = JSON.parse(data);
            res.render('dtbverschilkaart', { resultMessage: "", resultGeojson: geojsonData});
        //Invalid geojson error
        } catch (parseError) {
            res.status(500).json({ error: "Error parsing GeoJSON file" });
        }
    })
    //Reset
    } else { res.render('dtbverschilkaart', { resultMessage: "", resultGeojson: ""}); }
});

////////////////////////////////////////
//     Upload file configuration    //
////////////////////////////////////////
const multer = require('multer');
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, 'data/temp/')
    },
    filename: (req, file, cb) => {
        cb(null, file.fieldname + path.extname(file.originalname))
    }
});
const fileLimits = { fileSize: 30000000}
const upload = multer({ storage: storage, limits: fileLimits});
const uploadFields = upload.fields([
    { name: 'uitsnede', maxCount: 1 },
    { name: 'mutatie', maxCount: 1 }
]);

////////////////////////////////////////
//      Create new geojson file       //
////////////////////////////////////////
router.post('/dtbverschilkaart/create', uploadFields, (req, res) => {
    // Rename to randomly generated number
    const oldNameUitsnede = 'data/temp/uitsnede.zip';
    const oldNameMutatie = 'data/temp/mutatie.zip';
    const randomNumber = Math.floor(100000 + Math.random() * 900000);
    const newNameUitsnede = `data/temp/${randomNumber}_u.zip`;
    const newNameMutatie = `data/temp/${randomNumber}_m.zip`;

    fs.rename(oldNameUitsnede, newNameUitsnede, (err) => {
        if (err) {
            console.log('Error: Geen .zip bestand', err);
        } else {
        }
    });

    fs.rename(oldNameMutatie, newNameMutatie, (err) => {
        if (err) {
            console.log('Error: Geen .zip bestand', err);
        } else {
        }
    });

    // Execute verschilkaart.py
    var spawn = require('child_process').spawn;
    var process = spawn('python', ['./scripts/verschilkaart.py', randomNumber]);

    process.on('error', (err) => {
        console.error('Failed to start subprocess:', err);
    });

    var pyresults = '';
    process.stdout.on('data', function (data) {
        pyresults += data.toString();
    });

    process.stderr.on('data', (data) => {
        console.error('Python error:', data.toString());
    });

    // Response python output
    var resultLink = `${req.protocol}://${req.get('host')}/dtbverschilkaart?geojsonId=${randomNumber}`;
    process.on('close', (code) => {
        res.render('createkaart', { resultMessage: pyresults, resultLink: resultLink});
    });
});

module.exports = router;