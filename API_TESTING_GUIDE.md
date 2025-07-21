# API Testing Guide

## Overview
This FastAPI application processes PDF documents and answers questions about them using OpenAI's GPT-4.

## Authentication
- **Bearer Token Required**: `1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c`
- Add to headers: `Authorization: Bearer YOUR_TOKEN`

## Input Format

### Request Body
```json
{
  "documents": "https://example.com/your-document.pdf",
  "questions": [
    "Question 1",
    "Question 2",
    "Question 3"
  ]
}
```

### Requirements
- **documents**: Must be a valid HTTPS URL to a PDF file
- **questions**: Array of strings (your questions about the document)
- PDF must be publicly accessible (no authentication required on the PDF URL)

## Testing Methods

### 1. Python Test Script
```bash
python test_api.py
```

### 2. cURL Commands
```bash
./curl_examples.sh
```

### 3. Manual cURL
```bash
curl -X POST "http://localhost:8000/api/v1/hackrx/run" \
  -H "Authorization: Bearer 1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "YOUR_PDF_URL",
    "questions": ["Question 1", "Question 2"]
  }'
```

## Making PDFs Accessible for Testing

### Option 1: Use Public PDF URLs
- Government documents
- Public research papers
- Sample PDFs (like W3C test PDFs)

### Option 2: Upload to File Sharing Service
1. Upload your PDF to:
   - Google Drive (make link public)
   - Dropbox (create sharing link)
   - GitHub (raw file URL)
   - Any file hosting service

### Option 3: Local File Server
```bash
# In directory with your PDF:
python -m http.server 8080

# Then use: http://localhost:8080/your-file.pdf
```

### Option 4: Use ngrok for Local Files
```bash
# Install ngrok, then:
ngrok http 8080
# Use the provided HTTPS URL
```

## Example Questions to Test
- "What is the main topic of this document?"
- "What are the key dates mentioned?"
- "Who are the parties involved?"
- "What are the main obligations or requirements?"
- "Are there any financial amounts mentioned?"
- "What is the document type?"

## Troubleshooting

### Common Issues:
1. **403 Forbidden**: Check your auth token
2. **400 Bad Request**: Verify PDF URL is accessible
3. **500 Server Error**: Check OpenAI API key in .env file
4. **Connection Refused**: Ensure server is running on port 8000

### Server Logs
The server will show detailed logs for each request, including:
- Document download status
- Text extraction progress
- OpenAI API calls
- Any errors encountered