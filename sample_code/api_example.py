#!/usr/bin/env python3
"""Example Python file with API calls and dependencies."""

import requests  # This is a dependency
import json
import os
from pathlib import Path
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import urllib and httpx to have multiple HTTP libraries (dependencies)
import urllib.request
import httpx  # Another dependency

# Import the same dependency multiple times in different ways
from requests.exceptions import RequestException
from requests import Session
import requests.auth  # Same dependency, different import

class APIClient:
    """Example API client class."""
    
    def __init__(self, base_url="https://api.example.com", api_key=None):
        """Initialize the API client."""
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        # Set up auth headers if API key is provided
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
    
    def get_users(self):
        """Get users from the API."""
        url = f"{self.base_url}/users"
        logger.info(f"Fetching users from {url}")
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Error fetching users: {e}")
            return None
    
    def create_user(self, user_data):
        """Create a new user."""
        url = f"{self.base_url}/users"
        logger.info(f"Creating user at {url}")
        
        try:
            response = self.session.post(url, json=user_data)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Error creating user: {e}")
            return None

# Example of direct API calls
def fetch_weather(city):
    """Fetch weather data for a city."""
    api_key = os.environ.get("WEATHER_API_KEY", "demo_key")
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"
    
    # Using requests directly
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Using urllib
def fetch_data_with_urllib():
    """Fetch data using urllib."""
    url = "https://jsonplaceholder.typicode.com/todos/1"
    
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        return data

# Using httpx
async def fetch_async_data():
    """Fetch data using httpx async client."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts/1")
        return response.json()

# Same URLs but with different auth methods
def fetch_with_auth():
    """Fetch data with different auth methods."""
    # Basic auth
    response = requests.get("https://api.github.com/user", auth=("username", "password"))
    
    # Token auth
    headers = {"Authorization": "Bearer token123"}
    response = requests.get("https://api.github.com/user", headers=headers)
    
    # API key
    params = {"api_key": "my_api_key"}
    response = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params)

if __name__ == "__main__":
    # Create API client and make calls
    client = APIClient(api_key="test_key")
    users = client.get_users()
    
    # Create a new user
    new_user = {
        "name": "John Doe",
        "email": "john@example.com"
    }
    created_user = client.create_user(new_user)
    
    # Fetch weather
    weather = fetch_weather("London")
    
    # Fetch data with urllib
    todo = fetch_data_with_urllib()
    
    print("Done fetching data") 