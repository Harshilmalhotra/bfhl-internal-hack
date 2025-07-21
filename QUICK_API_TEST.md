# Quick API Testing Guide

## Available Endpoints

### 1. Root Endpoint (GET)
```bash
curl https://your-app.vercel.app/
```

### 2. Health Check (GET)
```bash
curl https://your-app.vercel.app/health
```

### 3. Document Processing (POST)
```bash
curl -X POST https://your-app.vercel.app/api/v1/hackrx/run \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/sample.pdf",
    "questions": ["What is this document about?", "What are the key points?"]
  }'
```

## Common Errors

### "Method Not Allowed"
- You're using GET on a POST endpoint or vice versa
- Make sure to use `-X POST` for the `/api/v1/hackrx/run` endpoint

### Testing in Browser
- You can only test GET endpoints in browser:
  - `https://your-app.vercel.app/` - Should show API info
  - `https://your-app.vercel.app/health` - Should show {"status": "healthy"}

### Testing with Postman
1. Import the `HackRx_API_Collection.postman_collection.json`
2. Update the base URL to your Vercel deployment
3. Run the requests

## Quick Test Script
Save this as `test_vercel.sh` and run it:

```bash
#!/bin/bash

# Replace with your actual Vercel URL
API_URL="https://your-app.vercel.app"

echo "Testing Health Endpoint..."
curl -s "$API_URL/health" | jq .

echo -e "\n\nTesting Root Endpoint..."
curl -s "$API_URL/" | jq .

echo -e "\n\nTesting Document Processing..."
curl -s -X POST "$API_URL/api/v1/hackrx/run" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "questions": ["What is this document about?"]
  }' | jq .
```

Make it executable: `chmod +x test_vercel.sh`
Run it: `./test_vercel.sh`