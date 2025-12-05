#!/usr/bin/env python3
"""
Verification script for API documentation.

This script verifies that all spell application endpoints and schemas
are properly documented in the OpenAPI specification.
"""

from app.main import app
import json


def verify_endpoints():
    """Verify that spell application endpoints exist and are documented."""
    schema = app.openapi()
    
    print("=" * 70)
    print("API DOCUMENTATION VERIFICATION")
    print("=" * 70)
    
    # Check endpoints
    print("\n1. ENDPOINTS")
    print("-" * 70)
    
    endpoints = {
        '/api/spells/{spell_id}/apply': {
            'method': 'post',
            'name': 'Apply Spell'
        },
        '/api/spells/{spell_id}/applications': {
            'method': 'get',
            'name': 'List Spell Applications'
        }
    }
    
    for endpoint, info in endpoints.items():
        if endpoint in schema['paths']:
            method_data = schema['paths'][endpoint].get(info['method'], {})
            description = method_data.get('description', 'NO DESCRIPTION')
            
            print(f"\n✓ {info['name']}")
            print(f"  Endpoint: {info['method'].upper()} {endpoint}")
            print(f"  Description: {description[:100]}...")
            
            # Check for HTTP status codes in description
            if 'HTTP Status Codes' in description:
                print(f"  ✓ HTTP status codes documented")
            else:
                print(f"  ✗ HTTP status codes NOT documented")
            
            # Check for examples
            if 'Example' in description:
                print(f"  ✓ Examples provided")
            else:
                print(f"  ✗ Examples NOT provided")
        else:
            print(f"\n✗ {info['name']} - NOT FOUND")
    
    # Check schemas
    print("\n\n2. SCHEMAS")
    print("-" * 70)
    
    schemas = [
        'SpellApplicationRequest',
        'SpellApplicationResponse',
        'SpellApplicationSummary',
        'FailingContext',
        'AdaptationConstraints'
    ]
    
    for schema_name in schemas:
        if schema_name in schema['components']['schemas']:
            s = schema['components']['schemas'][schema_name]
            properties = s.get('properties', {})
            
            print(f"\n✓ {schema_name}")
            print(f"  Description: {s.get('description', 'N/A')[:80]}...")
            print(f"  Properties: {len(properties)}")
            
            # Check if all properties have descriptions
            props_with_desc = sum(1 for p in properties.values() if 'description' in p)
            print(f"  Properties with descriptions: {props_with_desc}/{len(properties)}")
            
            # Check if properties have examples
            props_with_examples = sum(1 for p in properties.values() if 'examples' in p)
            print(f"  Properties with examples: {props_with_examples}/{len(properties)}")
        else:
            print(f"\n✗ {schema_name} - NOT FOUND")
    
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print("\nTo view the interactive documentation, start the server and visit:")
    print("  http://localhost:8000/docs")
    print("\n")


if __name__ == "__main__":
    verify_endpoints()
