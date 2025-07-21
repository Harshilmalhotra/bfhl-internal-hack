# Postman Testing Guide

## Quick Start

### Option 1: Import Collection
1. Open Postman
2. Click "Import" button
3. Select `HackRx_API_Collection.postman_collection.json`
4. Collection will appear in your workspace

### Option 2: Manual Setup
Follow the steps below to create requests manually.

## Manual Request Setup

### 1. Health Check
- **Method**: GET
- **URL**: `http://localhost:8000/health`
- **Headers**: None required

### 2. Process Document (Main Endpoint)
- **Method**: POST
- **URL**: `http://localhost:8000/api/v1/hackrx/run`
- **Headers**:
  - `Authorization`: Bearer 1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c
  - `Content-Type`: application/json
  - `Accept`: application/json

- **Body** (raw JSON):
```json
{
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D",
    "questions": [
        "What is the grace period for premium payment under the National Parivar Mediclaim Plus Policy?",
        "What is the waiting period for pre-existing diseases (PED) to be covered?",
        "Does this policy cover maternity expenses, and what are the conditions?",
        "What is the waiting period for cataract surgery?",
        "Are the medical expenses for an organ donor covered under this policy?",
        "What is the No Claim Discount (NCD) offered in this policy?",
        "Is there a benefit for preventive health check-ups?",
        "How does the policy define a 'Hospital'?",
        "What is the extent of coverage for AYUSH treatments?",
        "Are there any sub-limits on room rent and ICU charges for Plan A?"
    ]
}
```

## Setting Up Authorization in Postman

### Bearer Token Method:
1. Go to the "Authorization" tab
2. Select "Bearer Token" from the Type dropdown
3. Enter token: `1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c`

### Manual Header Method:
1. Go to the "Headers" tab
2. Add:
   - Key: `Authorization`
   - Value: `Bearer 1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c`

## Expected Responses

### Successful Response (200 OK):
```json
{
    "answers": [
        "A grace period of thirty days is provided...",
        "There is a waiting period of thirty-six (36) months...",
        // ... more answers
    ]
}
```

### Authentication Error (403 Forbidden):
```json
{
    "detail": "Invalid authentication token"
}
```

### Server Error (500):
```json
{
    "detail": "Error message describing the issue"
}
```

## Testing Tips

1. **Verify Server is Running**: Check http://localhost:8000/health first
2. **Check Console Logs**: Your FastAPI server will show detailed logs
3. **Test Auth First**: Try with invalid token to ensure auth is working
4. **Use Console**: View Postman Console (View → Show Postman Console) for request details
5. **Response Time**: Document processing may take 30-60 seconds depending on PDF size

## Troubleshooting

- **Connection refused**: Ensure server is running (`python app.py` or `uvicorn app:app`)
- **403 Forbidden**: Check authorization token is correct
- **500 Error**: Check server logs and ensure OpenAI API key is set in .env
- **Timeout**: Large PDFs may take time; increase timeout in Postman settings

## Environment Variables (Optional)
You can create Postman environment variables:
- `baseUrl`: http://localhost:8000
- `authToken`: 1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c

Then use `{{baseUrl}}` and `{{authToken}}` in your requests.