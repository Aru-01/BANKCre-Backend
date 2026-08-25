import logging
import os
import json
from django.conf import settings

logger = logging.getLogger(__name__)

def extract_property_details(name, address, lat=None, lng=None):
    try:
        import anthropic
    except ImportError:
        return {}
    
    api_key = getattr(settings, 'CLAUDE_API_KEY', '') or os.getenv('CLAUDE_API_KEY', '')
    if not api_key:
        return {}
        
    client = anthropic.Anthropic(api_key=api_key)
    
    location_str = f"Property Name: {name}\nProperty Address: {address}"
    if lat and lng:
        location_str += f"\nLatitude: {lat}\nLongitude: {lng}"
        
    prompt = f"""
Given the following property details, please extract or estimate the property metrics. 
To ensure maximum accuracy, first use your internal knowledge to recall specific facts about this property (e.g., exact opening year, exact number of rooms, total area) in a brief reasoning step.
If this is a known property or hotel, do NOT return null if you can make a highly educated estimate. 
Return ONLY a valid JSON object with these exact keys:
- _reasoning (string: write a short 1-2 sentence factual recall about the property to ensure accuracy)
- property_type (MUST be one of exactly: "multifamily", "retail", "industrial", "office", "other", or null. For a hotel, use "other".)
- number_of_units (integer or null. For a hotel, this is the exact number of rooms.)
- rentable_area (float or null. Total square footage approx.)
- year_built (integer or null. The exact year it opened/was built.)
- occupancy_rate (float or null. e.g., 0.75 for 75%)
- year_renovated (integer or null)
- parking_spaces (integer or null)

{location_str}
"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system="You are a helpful assistant that strictly returns valid JSON with no markdown formatting.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            extra_body={"temperature": 0.0}
        )
        text = response.content[0].text.strip()
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            return json.loads(json_str)
    except Exception as e:
        logger.warning(f"Claude extraction failed: {e}")
    return {}
