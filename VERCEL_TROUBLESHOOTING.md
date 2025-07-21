# Vercel Deployment Troubleshooting

## Common Issues and Solutions

### 1. 500 Internal Server Error (FUNCTION_INVOCATION_FAILED)

This error typically occurs due to:

#### Missing Environment Variables
- **Solution**: Ensure you've added the required environment variables in Vercel:
  1. Go to your Vercel project dashboard
  2. Navigate to Settings > Environment Variables
  3. Add:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `AUTH_TOKEN`: Your authentication token (optional)

#### Import Errors
- **Solution**: The app structure has been updated to handle imports correctly:
  - Use `api/main.py` as the entry point
  - The handler properly adds the parent directory to the Python path

### 2. Module Not Found Errors

If you see errors like "No module named 'fastapi'":
- **Solution**: Ensure all dependencies are in `requirements.txt`
- Vercel automatically installs packages from `requirements.txt`

### 3. Timeout Errors

If your function times out:
- **Solution**: 
  - Vercel has a 10-second timeout for hobby accounts
  - Consider optimizing your PDF processing
  - For larger documents, consider using Vercel Pro (60-second timeout)

### 4. Memory Errors

If you encounter memory issues:
- **Solution**: 
  - The free tier has 1024 MB memory limit
  - Large PDFs might exceed this
  - Consider implementing file size limits

## Deployment Checklist

Before deploying, ensure:

1. ✅ Environment variables are set in Vercel dashboard
2. ✅ `requirements.txt` includes all dependencies
3. ✅ `api/main.py` exists and imports correctly
4. ✅ `vercel.json` points to `api/main.py`
5. ✅ Your OpenAI API key has sufficient credits
6. ✅ The base URL for OpenAI is correctly configured

## Testing Your Deployment

1. **Check the health endpoint first**:
   ```bash
   curl https://your-app.vercel.app/health
   ```

2. **Test with a simple request**:
   ```bash
   curl -X POST https://your-app.vercel.app/api/v1/hackrx/run \
     -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "documents": "https://example.com/sample.pdf",
       "questions": ["What is this document about?"]
     }'
   ```

## Viewing Logs

To debug issues:
1. Go to your Vercel project dashboard
2. Click on "Functions" tab
3. Click on the failing function
4. View the logs for detailed error messages

## Alternative: Local Testing

Before deploying, test locally with Vercel CLI:
```bash
# Install Vercel CLI
npm i -g vercel

# Run locally
vercel dev
```

This will simulate the Vercel environment locally.