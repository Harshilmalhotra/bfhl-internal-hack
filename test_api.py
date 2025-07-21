import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:", response.json())
    return response.status_code == 200

def test_root():
    """Test root endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print("Root Endpoint:", response.json())
    return response.status_code == 200

def test_document_processing():
    """Test document processing with sample PDF"""
    # Using the exact sample from the API specification
    payload = {
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
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting document processing...")
    print(f"URL: {BASE_URL}/api/v1/hackrx/run")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/hackrx/run",
        json=payload,
        headers=headers
    )
    
    print(f"\nStatus Code: {response.status_code}")
    if response.status_code == 200:
        print("Response:", json.dumps(response.json(), indent=2))
    else:
        print("Error:", response.text)
    
    return response.status_code == 200

def test_invalid_auth():
    """Test with invalid authentication"""
    payload = {
        "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D",
        "questions": ["Test question"]
    }
    
    headers = {
        "Authorization": "Bearer invalid_token",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting invalid authentication...")
    response = requests.post(
        f"{BASE_URL}/api/v1/hackrx/run",
        json=payload,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print("Response:", response.text)
    
    return response.status_code == 403

if __name__ == "__main__":
    print("Starting API tests...\n")
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("Document Processing", test_document_processing),
        ("Invalid Auth", test_invalid_auth)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            print(f"Running: {test_name}")
            print(f"{'='*50}")
            result = test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
        except Exception as e:
            print(f"Error: {e}")
            results.append((test_name, f"ERROR: {str(e)}"))
    
    print(f"\n{'='*50}")
    print("TEST RESULTS")
    print(f"{'='*50}")
    for test_name, result in results:
        print(f"{test_name}: {result}")