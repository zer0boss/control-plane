"""
Direct test: Check if Control Plane's message handler is being called
"""
import asyncio
import json
import requests

# First, get the connector and check its state
response = requests.get("http://localhost:8000/api/v1/instances")
instances = response.json()
print("Instances:", json.dumps(instances, indent=2))

# Check if any instance is connected
for item in instances.get('items', []):
    print(f"\nInstance: {item['name']} ({item['id']})")
    print(f"  Status: {item['status']}")
    print(f"  Health: {item.get('health', {})}")
