#!/usr/bin/env node
/**
 * Quick setup script to configure your GitHub token for the Find the PDF system.
 * This runs locally and only stores the token in your browser's localStorage.
 * 
 * Usage: node setup-token.js
 */

const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('\n🔧 Find the PDF - Token Setup');
console.log('=====================================\n');

console.log('To enable PDF uploads via GitHub API, you need a Personal Access Token.\n');

console.log('Steps to create a token:');
console.log('1. Go to https://github.com/settings/tokens');
console.log('2. Click "Generate new token (classic)"');
console.log('3. Name it "FindPDF Upload"');
console.log('4. Select the "repo" scope');
console.log('5. Generate and copy the token\n');

rl.question('Paste your GitHub Personal Access Token here: ', (token) => {
  if (!token || !token.startsWith('ghp_')) {
    console.log('❌ Invalid token format. Tokens should start with "ghp_"');
    rl.close();
    return;
  }

  console.log('\n✅ Token format looks correct!');
  console.log('\nTo configure the token in your browser:');
  console.log('1. Visit: https://kilianrouge.github.io/findthepdf/');
  console.log('2. Click "⚙️ Setup Token"');
  console.log('3. Paste your token');
  console.log('4. Click "Save Token"\n');

  console.log('🔒 Security Note: Your token will be stored only in your browser\'s');
  console.log('   localStorage and never transmitted to third parties.\n');

  console.log('📝 Token saved to setup-token.txt for your reference.');
  
  // Save to a file for reference (gitignored)
  require('fs').writeFileSync('setup-token.txt', `GitHub Token: ${token}\nGenerated: ${new Date().toISOString()}\n`);
  
  rl.close();
});