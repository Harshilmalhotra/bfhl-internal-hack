# Document Intelligence API

A webhook service that processes documents (PDFs), extracts information, and provides intelligent Q&A responses.

## Features

- Document download and PDF text extraction
- Document classification and entity extraction
- Text cleaning and structuring
- Question-answering based on document content
- Bearer token authentication
- RESTful API design

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Add your OpenAI API key to `.env`:
```
OPENAI_API_KEY=your_actual_openai_api_key
```

4. Run the application:
```bash
python app.py
```

## API Usage

### Endpoint: POST /api/v1/hackrx/run

**Headers:**
- Content-Type: application/json
- Authorization: Bearer 1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c

**Request Body:**
```json
{
    "documents": "https://example.com/document.pdf",
    "questions": [
        "Question 1?",
        "Question 2?"
    ]
}
```

**Response:**
```json
{
    "answers": [
        "Answer to question 1",
        "Answer to question 2"
    ]
}
```

## Docker Deployment

Build and run with Docker:
```bash
docker build -t document-intelligence-api .
docker run -p 8000:8000 --env-file .env document-intelligence-api
```

## Testing

Test the API with curl:
```bash
curl -X POST http://localhost:8000/api/v1/hackrx/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c" \
  -d '{
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D",
    "questions": ["What is the grace period for premium payment?"]
  }'
```