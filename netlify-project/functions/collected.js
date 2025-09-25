const fs = require('fs');
const path = require('path');

const PDF_DIR = path.join(__dirname, '../PDF');

exports.handler = async () => {
  let bibkeys = [];
  if (fs.existsSync(PDF_DIR)) {
    bibkeys = fs.readdirSync(PDF_DIR)
      .filter(f => f.endsWith('.pdf'))
      .map(f => f.replace(/\.pdf$/, ''));
  }
  return {
    statusCode: 200,
    body: JSON.stringify(bibkeys),
    headers: { 'Content-Type': 'application/json' }
  };
};
