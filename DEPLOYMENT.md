# Deployment Guide for Document Intelligence API

## Deploying to Vercel

### Prerequisites
1. A Vercel account (sign up at https://vercel.com)
2. Vercel CLI installed (optional): `npm i -g vercel`

### Step 1: Prepare Environment Variables
1. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```
2. Set your OpenAI API key and authentication token.

### Step 2: Deploy to Vercel

#### Option A: Using Vercel CLI
1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Deploy:
   ```bash
   vercel
   ```

4. Follow the prompts and set environment variables when asked.

#### Option B: Using GitHub Integration
1. Push your code to a GitHub repository
2. Go to https://vercel.com/new
3. Import your GitHub repository
4. Add environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `AUTH_TOKEN`: Your authentication token (optional)
5. Click "Deploy"

### Step 3: Configure Environment Variables in Vercel
1. Go to your project settings in Vercel dashboard
2. Navigate to "Environment Variables"
3. Add:
   - `OPENAI_API_KEY`
   - `AUTH_TOKEN` (if you want to override the default)

### API Endpoints
Once deployed, your API will be available at:
- Main endpoint: `https://your-project.vercel.app/api/v1/hackrx/run`
- Health check: `https://your-project.vercel.app/health`
- Root: `https://your-project.vercel.app/`

### Testing the Deployment
Use the provided test scripts with your deployed URL:
```bash
# Update the URL in test scripts
export API_URL="https://your-project.vercel.app"
./test_request.sh
```

## Alternative Deployment Options

### Deploy to Render
1. Create a `render.yaml`:
   ```yaml
   services:
     - type: web
       name: document-intelligence-api
       env: python
       buildCommand: "pip install -r requirements.txt"
       startCommand: "uvicorn app:app --host 0.0.0.0 --port $PORT"
       envVars:
         - key: OPENAI_API_KEY
           sync: false
         - key: AUTH_TOKEN
           sync: false
   ```

2. Connect your GitHub repository to Render
3. Deploy

### Deploy to Railway
1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Add environment variables: `railway variables set OPENAI_API_KEY=your_key`
5. Deploy: `railway up`

### Deploy to Heroku
1. Create a `Procfile`:
   ```
   web: uvicorn app:app --host 0.0.0.0 --port $PORT
   ```

2. Create a `runtime.txt`:
   ```
   python-3.11.0
   ```

3. Deploy:
   ```bash
   heroku create your-app-name
   heroku config:set OPENAI_API_KEY=your_key
   git push heroku main
   ```

## Important Notes
- Keep your API keys secure and never commit them to version control
- The default AUTH_TOKEN in the code should be changed for production
- Monitor your OpenAI API usage to avoid unexpected costs
- Consider implementing rate limiting for production use