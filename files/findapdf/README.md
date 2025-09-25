# Find the PDF - Instructions

This system provides a web interface for contributors to find and upload PDF files for academic papers based on bibliography entries.

## How it works

1. **User Assignment**: Each user gets a unique fingerprint based on their browser characteristics
2. **Random Entry**: Users are assigned a random bibliography entry from the BibTeX file
3. **20-minute Lock**: Once assigned, the entry is locked for 20 minutes to prevent duplicate assignments
4. **File Upload**: Users can drag-and-drop or browse for PDF files
5. **GitHub Integration**: Files are uploaded directly to your GitHub repository using the GitHub API
6. **Automatic Naming**: Uploaded PDFs are renamed to match the bibliography key and committed to the repo

## Setup Instructions

### For Repository Owner (One-time setup)

1. **Create a GitHub Personal Access Token**:
   - Go to [GitHub Settings → Personal Access Tokens](https://github.com/settings/tokens)
   - Click "Generate new token (classic)"
   - Give it a name like "FindPDF Upload"
   - Select the **"repo"** scope (full control of repositories)
   - Click "Generate token"
   - **Important**: Copy the token immediately (you won't see it again)

2. **Configure the Token**:
   - Visit your `/findthepdf/` page
   - Click the "⚙️ Setup Token" button
   - Paste your token and click "Save Token"
   - The button should turn green with "✅ Token Configured"

### For Contributors (Users uploading PDFs)

No setup required! The token is already configured by the repository owner.

## Features

- **Hidden Page**: Accessible only at `/findthepdf/` (not linked in navigation)
- **Responsive Design**: Works on desktop and mobile devices
- **File Validation**: Only accepts PDF files up to 50MB
- **GitHub API Integration**: Direct upload to repository (completely free!)
- **Progress Tracking**: Visual feedback during upload process
- **Token Management**: Secure GitHub authentication system
- **Next Button**: Users can get a new assignment after completing one

## File Structure

```
files/findapdf/
├── findapdf_tofind.bib    # Source bibliography file
├── PDFs/                  # Directory for uploaded PDF files (auto-created)
├── upload.php             # Legacy server-side script (not needed with GitHub API)
└── README.md              # This file
```

## GitHub API Benefits

✅ **Completely Free**: Uses GitHub's free API  
✅ **No Server Required**: Works with static GitHub Pages  
✅ **Automatic Version Control**: All uploads are tracked in git history  
✅ **Secure**: Uses GitHub's authentication system  
✅ **Reliable**: Built on GitHub's infrastructure  

## Access

The page is accessible at: `https://kilianrouge.github.io/findthepdf/`

## Technical Notes

### GitHub API Integration

The system now uses GitHub's API to upload files directly to your repository:

1. **Authentication**: Uses GitHub Personal Access Tokens
2. **File Storage**: PDFs are committed directly to `files/findapdf/PDFs/`
3. **Naming**: Files are automatically renamed to `{bibkey}.pdf`
4. **Version Control**: All uploads create git commits with descriptive messages
5. **Security**: Tokens are stored locally in browser localStorage

### No Server Required! 

This solution is **completely free** and requires **no additional hosting**:
- ✅ Works with GitHub Pages (static hosting)
- ✅ Uses GitHub's free API (no rate limits for typical usage)
- ✅ No PHP/server-side code needed
- ✅ No monthly fees or external services

### Browser Fingerprinting

The system uses a combination of browser characteristics to create a unique identifier:
- User agent string
- Language settings  
- Screen resolution
- Timezone offset
- Canvas fingerprint

This is more reliable than IP addresses for client-side applications and works across different networks.

### Data Persistence

User assignments are stored in `localStorage`, which means:
- Data persists across browser sessions
- Data is isolated per domain
- Users can clear their assignment by clearing browser data
- No server-side database required

## Bibliography Format

The system expects BibTeX entries with these fields:
- `title`: Paper title
- `author`: Author(s)
- `date`: Publication date/year
- `doi`: Digital Object Identifier (optional)

Example entry:
```bibtex
@article{ExampleKey2024,
  title = {Example Paper Title},
  author = {Author Name},
  date = {2024},
  doi = {10.1000/example},
}
```

## Customization

You can customize the appearance by modifying the CSS in `findthepdf.html`:
- Colors and styling
- Upload area appearance
- Button styles
- Layout and spacing

## Security Considerations

- File type validation (PDF only)
- File size limits (50MB maximum)
- Filename sanitization (bibkey-based naming)
- No executable file uploads
- Client-side validation with server-side verification (when using PHP script)

## Troubleshooting

### Common Issues

1. **Bibliography not loading**: Check that the BibTeX file path is correct
2. **Same entry appearing**: Clear browser localStorage or wait 20 minutes
3. **Upload not working**: This is expected on GitHub Pages (static site)
4. **File not accepted**: Ensure file is PDF format and under 50MB

### Browser Support

- Modern browsers with JavaScript enabled
- File API support required for drag-and-drop
- localStorage support required for user tracking
- Canvas API for fingerprinting

## Future Enhancements

Possible improvements:
- Admin interface to view upload statistics
- Progress tracking across all entries
- Email notifications for new uploads
- Integration with reference management systems
- Automatic DOI validation
- Duplicate detection