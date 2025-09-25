const fs = require('fs');
const path = require('path');
const multer = require('multer');

const upload = multer({
  storage: multer.diskStorage({
    destination: path.join(__dirname, '../PDF'),
    filename: (req, file, cb) => {
      const bibkey = req.body.bibkey || 'unknown';
      cb(null, bibkey + '.pdf');
    }
  }),
  limits: { fileSize: 50 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf') cb(null, true);
    else cb(new Error('Only PDF files allowed'));
  }
});

exports.handler = async (event, context) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }
  return new Promise((resolve, reject) => {
    const req = {
      headers: event.headers,
      body: event.body,
      method: event.httpMethod,
      rawBody: Buffer.from(event.body, event.isBase64Encoded ? 'base64' : 'utf8'),
      ...event
    };
    const res = {
      status: code => { res.statusCode = code; return res; },
      send: msg => resolve({ statusCode: res.statusCode || 200, body: msg }),
      statusCode: 200
    };
    upload.single('pdf')(req, res, err => {
      if (err) {
        resolve({ statusCode: 400, body: err.message });
      } else {
        resolve({ statusCode: 200, body: 'Uploaded' });
      }
    });
  });
};
