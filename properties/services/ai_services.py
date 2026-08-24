import logging
import os
import json
from django.conf import settings

logger = logging.getLogger(__name__)

def extract_property_details(name, address):
    try:
        from openai import OpenAI
    except ImportError:
        return {}
    
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        return {}
        
    client = OpenAI(api_key=api_key)
    prompt = f"""
Given the following property name and address, please estimate or extract the following details. If you are unsure or cannot find the data, return null or 0. Return ONLY a valid JSON object with these exact keys:
- property_type (MUST be one of exactly: "multifamily", "retail", "industrial", "office", "other", or null)
- number_of_units (integer or null)
- rentable_area (float or null)
- year_built (integer or null)
- occupancy_rate (float or null)
- year_renovated (integer or null)
- parking_spaces (integer or null)

Property Name: {name}
Property Address: {address}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that strictly returns valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        text = response.choices[0].message.content
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            return json.loads(json_str)
    except Exception as e:
        logger.warning(f"OpenAI extraction failed: {e}")
    return {}
