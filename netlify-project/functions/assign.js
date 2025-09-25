const fs = require('fs');
const path = require('path');

const ASSIGNMENTS_PATH = path.join(__dirname, '../assignments.json');

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }
  const { ip, bibkey } = JSON.parse(event.body);
  let assignments = {};
  if (fs.existsSync(ASSIGNMENTS_PATH)) {
    assignments = JSON.parse(fs.readFileSync(ASSIGNMENTS_PATH, 'utf8'));
  }
  assignments[ip] = { bibkey, timestamp: Date.now() };
  fs.writeFileSync(ASSIGNMENTS_PATH, JSON.stringify(assignments));
  return { statusCode: 200, body: 'Assigned' };
};
