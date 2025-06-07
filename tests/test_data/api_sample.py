"""Sample file with API calls for testing."""

import requests
import httpx

def test_api_calls():
    # Allowed API calls
    response = requests.get('https://api.github.com/users')
    weather = requests.get('https://api.openweathermap.org/data/2.5/weather')
    
    # Restricted API calls
    auth_response = requests.get('http://api.restricted-service.com/auth')
    
    # Internal APIs
    data = httpx.get('https://api.internal.example.com/data')
    auth = requests.post('https://auth.example.com/login')

if __name__ == '__main__':
    test_api_calls()
