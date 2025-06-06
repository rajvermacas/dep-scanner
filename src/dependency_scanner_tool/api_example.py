"""Example file with REST API calls for testing the API call detection feature."""

import requests
import urllib.request
import json
import httpx


def get_users():
    """Get a list of users from a REST API."""
    response = requests.get('https://api.example.com/users')
    return response.json()


def create_user(name, email):
    """Create a new user via a REST API."""
    data = {'name': name, 'email': email}
    headers = {'Content-Type': 'application/json'}
    response = requests.post('https://api.example.com/users', json=data, headers=headers)
    return response.json()


def get_user_details(user_id):
    """Get details for a specific user."""
    url = f'https://api.example.com/users/{user_id}'
    response = requests.get(url)
    return response.json()


def update_user(user_id, data):
    """Update a user's information."""
    url = f'https://api.example.com/users/{user_id}'
    headers = {'Authorization': 'Bearer my-token'}
    response = requests.put(url, json=data, headers=headers)
    return response.json()


def delete_user(user_id):
    """Delete a user."""
    url = f'https://api.example.com/users/{user_id}'
    response = requests.delete(url)
    return response.status_code


def authenticate():
    """Authenticate with the API."""
    auth_data = {'username': 'admin', 'password': 'secret'}
    response = requests.post('https://api.example.com/auth', json=auth_data)
    return response.json().get('token')


def get_data_with_urllib():
    """Get data using urllib."""
    url = 'https://api.example.com/data'
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode('utf-8'))


def post_data_with_urllib(data):
    """Post data using urllib."""
    url = 'https://api.example.com/data'
    data_bytes = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=data_bytes, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))


async def get_async_data():
    """Get data using httpx async client."""
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com/async-data')
        return response.json()


def get_data_with_httpx():
    """Get data using httpx."""
    response = httpx.get('https://api.example.com/httpx-data')
    return response.json()


if __name__ == "__main__":
    # Make some API calls
    users = get_users()
    print(f"Found {len(users)} users")
    
    new_user = create_user("John Doe", "john@example.com")
    print(f"Created user: {new_user['id']}")
    
    user = get_user_details(new_user['id'])
    print(f"User details: {user}")
    
    updated_user = update_user(new_user['id'], {'name': 'John Smith'})
    print(f"Updated user: {updated_user}")
    
    delete_status = delete_user(new_user['id'])
    print(f"Delete status: {delete_status}")
    
    token = authenticate()
    print(f"Auth token: {token}")
    
    data = get_data_with_urllib()
    print(f"Data from urllib: {data}")
    
    httpx_data = get_data_with_httpx()
    print(f"Data from httpx: {httpx_data}") 