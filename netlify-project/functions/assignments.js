const fs = require('fs');
const path = require('path');

const ASSIGNMENTS_PATH = path.join(__dirname, '../assignments.json');

exports.handler = async () => {
  let assignments = {};
  if (fs.existsSync(ASSIGNMENTS_PATH)) {
    assignments = JSON.parse(fs.readFileSync(ASSIGNMENTS_PATH, 'utf8'));
  }
  return {
    statusCode: 200,
    body: JSON.stringify(assignments),
    headers: { 'Content-Type': 'application/json' }
  };
};
