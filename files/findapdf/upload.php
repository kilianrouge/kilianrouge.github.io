<?php
/**
 * File Upload Handler for Find the PDF
 * 
 * This is a server-side script that would need to be hosted on a server
 * that supports PHP to handle actual file uploads. Since GitHub Pages 
 * only supports static sites, you would need to:
 * 
 * 1. Host this on a separate server (like a VPS, shared hosting, etc.)
 * 2. Update the JavaScript to point to this server's URL
 * 3. Configure CORS headers to allow your GitHub Pages site to make requests
 * 
 * For a fully static solution, you might consider:
 * - Using a service like Netlify Forms
 * - Using a cloud storage service with direct upload APIs
 * - Using GitHub API to commit files directly to the repository
 */

header('Access-Control-Allow-Origin: https://kilianrouge.github.io');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

// Configuration
$upload_dir = __DIR__ . '/PDFs/';
$max_file_size = 50 * 1024 * 1024; // 50MB

// Create upload directory if it doesn't exist
if (!is_dir($upload_dir)) {
    mkdir($upload_dir, 0755, true);
}

// Check if file was uploaded
if (!isset($_FILES['pdf']) || $_FILES['pdf']['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    echo json_encode(['error' => 'No file uploaded or upload error']);
    exit;
}

$file = $_FILES['pdf'];
$bibkey = $_POST['bibkey'] ?? '';

// Validate inputs
if (empty($bibkey)) {
    http_response_code(400);
    echo json_encode(['error' => 'Bibkey is required']);
    exit;
}

// Validate file type
if ($file['type'] !== 'application/pdf') {
    http_response_code(400);
    echo json_encode(['error' => 'Only PDF files are allowed']);
    exit;
}

// Validate file size
if ($file['size'] > $max_file_size) {
    http_response_code(400);
    echo json_encode(['error' => 'File too large. Maximum size is 50MB']);
    exit;
}

// Sanitize bibkey for filename
$safe_bibkey = preg_replace('/[^a-zA-Z0-9\-_]/', '', $bibkey);
if (empty($safe_bibkey)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid bibkey']);
    exit;
}

$target_file = $upload_dir . $safe_bibkey . '.pdf';

// Move uploaded file
if (move_uploaded_file($file['tmp_name'], $target_file)) {
    // Log the upload
    $log_entry = [
        'timestamp' => date('Y-m-d H:i:s'),
        'bibkey' => $bibkey,
        'filename' => $safe_bibkey . '.pdf',
        'size' => $file['size'],
        'ip' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'
    ];
    
    file_put_contents(
        __DIR__ . '/upload_log.json',
        json_encode($log_entry) . "\n",
        FILE_APPEND | LOCK_EX
    );
    
    echo json_encode([
        'success' => true,
        'message' => 'File uploaded successfully',
        'filename' => $safe_bibkey . '.pdf'
    ]);
} else {
    http_response_code(500);
    echo json_encode(['error' => 'Failed to move uploaded file']);
}
?>