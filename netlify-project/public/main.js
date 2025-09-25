// main.js
// Handles UI, fetches random bib entry, manages upload and assignment logic

let bibEntries = [];
let currentEntry = null;
let userIP = null;
let selectedFile = null;

async function getIP() {
  // Use a public IP API
  const res = await fetch('https://api.ipify.org?format=json');
  const data = await res.json();
  return data.ip;
}

async function fetchBibEntries() {
  const res = await fetch('/findapdf_tofind.bib');
  const text = await res.text();
  // Parse BibTeX (simple parser for demo)
  const entries = [];
  const blocks = text.split(/(?=^@\w+\{)/gm).filter(b => b.trim().length > 0);
  blocks.forEach(block => {
    const header = block.match(/^@(\w+)\{([^,\s]+),/m);
    if (!header) return;
    const [, type, bibkey] = header;
    const entry = { type, bibkey };
    const fieldPattern = /(\w+)\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g;
    let m;
    while ((m = fieldPattern.exec(block)) !== null) {
      entry[m[1].toLowerCase()] = m[2].trim();
    }
    if (entry.title) entries.push(entry);
  });
  return entries;
}

async function fetchCollectedBibkeys() {
  const res = await fetch('/.netlify/functions/collected');
  if (!res.ok) return [];
  return await res.json();
}

async function fetchAssignments() {
  const res = await fetch('/.netlify/functions/assignments');
  if (!res.ok) return {};
  return await res.json();
}

function displayEntry(entry) {
  document.getElementById('entry-title').textContent = entry.title || 'No title';
  document.getElementById('entry-author').textContent = entry.author || 'No author';
  document.getElementById('entry-date').textContent = entry.date || 'No date';
  document.getElementById('entry-bibkey').textContent = entry.bibkey;
  const doiLink = document.getElementById('entry-doi');
  if (entry.doi) {
    doiLink.href = `https://doi.org/${entry.doi}`;
    doiLink.style.display = 'inline-block';
  } else {
    doiLink.style.display = 'none';
  }
}

function showMessage(msg, type) {
  const div = document.getElementById('messages');
  div.innerHTML = `<div class="${type}">${msg}</div>`;
}

function clearFileInfo() {
  document.getElementById('file-info').classList.add('hidden');
  document.getElementById('file-info').innerHTML = '';
  document.getElementById('upload-btn').disabled = true;
  selectedFile = null;
}

function handleFileSelect(file) {
  if (file.type !== 'application/pdf') {
    showMessage('Please select a PDF file.', 'error');
    return;
  }
  if (file.size > 50 * 1024 * 1024) {
    showMessage('File is too large. Maximum size is 50MB.', 'error');
    return;
  }
  selectedFile = file;
  const fileInfo = document.getElementById('file-info');
  fileInfo.innerHTML = `<strong>Selected:</strong> ${file.name}<br><strong>Size:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB`;
  fileInfo.classList.remove('hidden');
  document.getElementById('upload-btn').disabled = false;
}

document.addEventListener('DOMContentLoaded', async () => {
  userIP = await getIP();
  bibEntries = await fetchBibEntries();
  const collected = await fetchCollectedBibkeys();
  const assignments = await fetchAssignments();

  // Find assigned or available entry
  let assigned = assignments[userIP];
  let now = Date.now();
  let twentyMin = 20 * 60 * 1000;
  if (assigned && now - assigned.timestamp < twentyMin) {
    currentEntry = bibEntries.find(e => e.bibkey === assigned.bibkey);
  } else {
    // Remove expired assignments
    for (const ip in assignments) {
      if (now - assignments[ip].timestamp >= twentyMin) delete assignments[ip];
    }
    // Find available entries
    const assignedBibkeys = Object.values(assignments).map(a => a.bibkey);
    const available = bibEntries.filter(e => !collected.includes(e.bibkey) && !assignedBibkeys.includes(e.bibkey));
    if (available.length === 0) {
      currentEntry = bibEntries[Math.floor(Math.random() * bibEntries.length)];
    } else {
      currentEntry = available[Math.floor(Math.random() * available.length)];
    }
    // Assign
    await fetch('/.netlify/functions/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: userIP, bibkey: currentEntry.bibkey })
    });
  }
  displayEntry(currentEntry);

  // Upload area events
  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('file-input');
  uploadArea.addEventListener('click', () => fileInput.click());
  uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
  uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
  uploadArea.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', e => {
    if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
  });

  document.getElementById('upload-btn').addEventListener('click', async () => {
    if (!selectedFile || !currentEntry) return;
    const formData = new FormData();
    formData.append('pdf', selectedFile, currentEntry.bibkey + '.pdf');
    formData.append('bibkey', currentEntry.bibkey);
    const res = await fetch('/.netlify/functions/upload', {
      method: 'POST',
      body: formData
    });
    if (res.ok) {
      showMessage('PDF uploaded successfully!', 'success');
      clearFileInfo();
    } else {
      showMessage('Upload failed.', 'error');
    }
  });

  document.getElementById('next-btn').addEventListener('click', async () => {
    await fetch('/.netlify/functions/unassign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: userIP })
    });
    location.reload();
  });
});
