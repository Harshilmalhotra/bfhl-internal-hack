#!/bin/bash

# API Base URL
BASE_URL="http://localhost:8000"
AUTH_TOKEN="1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c"

echo "=== FastAPI Document Processing API - cURL Examples ==="
echo ""

# 1. Health Check
echo "1. Health Check:"
echo "----------------"
curl -X GET "${BASE_URL}/health"
echo -e "\n\n"

# 2. Root Endpoint
echo "2. Root Endpoint:"
echo "-----------------"
curl -X GET "${BASE_URL}/"
echo -e "\n\n"

# 3. Process Document (Valid Request - Using Sample from API Spec)
echo "3. Process Document with Authentication (HackRx Sample):"
echo "-------------------------------------------------------"
cat << 'EOF'
curl -X POST "${BASE_URL}/api/v1/hackrx/run" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D",
    "questions": [
        "What is the grace period for premium payment under the National Parivar Mediclaim Plus Policy?",
        "What is the waiting period for pre-existing diseases (PED) to be covered?",
        "Does this policy cover maternity expenses, and what are the conditions?",
        "What is the waiting period for cataract surgery?",
        "Are the medical expenses for an organ donor covered under this policy?",
        "What is the No Claim Discount (NCD) offered in this policy?",
        "Is there a benefit for preventive health check-ups?",
        "How does the policy define a '\''Hospital'\''?",
        "What is the extent of coverage for AYUSH treatments?",
        "Are there any sub-limits on room rent and ICU charges for Plan A?"
    ]
  }'
EOF

echo -e "\n\nExecuting..."
curl -X POST "${BASE_URL}/api/v1/hackrx/run" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D",
    "questions": [
        "What is the grace period for premium payment under the National Parivar Mediclaim Plus Policy?",
        "What is the waiting period for pre-existing diseases (PED) to be covered?",
        "Does this policy cover maternity expenses, and what are the conditions?",
        "What is the waiting period for cataract surgery?",
        "Are the medical expenses for an organ donor covered under this policy?",
        "What is the No Claim Discount (NCD) offered in this policy?",
        "Is there a benefit for preventive health check-ups?",
        "How does the policy define a '\''Hospital'\''?",
        "What is the extent of coverage for AYUSH treatments?",
        "Are there any sub-limits on room rent and ICU charges for Plan A?"
    ]
  }'
echo -e "\n\n"

# 4. Invalid Authentication
echo "4. Invalid Authentication Test:"
echo "------------------------------"
curl -X POST "${BASE_URL}/api/v1/hackrx/run" \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/test.pdf",
    "questions": ["Test question"]
  }'
echo -e "\n\n"

# 5. Using your own PDF
echo "5. Using Your Own PDF:"
echo "---------------------"
cat << 'EOF'
To use your own PDF file, replace the URL in the documents field:

curl -X POST "${BASE_URL}/api/v1/hackrx/run" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "YOUR_PDF_URL_HERE",
    "questions": [
      "Your first question?",
      "Your second question?",
      "Your third question?"
    ]
  }'

Note: The PDF must be publicly accessible via HTTP/HTTPS
EOF