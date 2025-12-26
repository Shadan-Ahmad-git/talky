#!/usr/bin/env python3
"""
Test script for Perplexity API integration.
Run this to verify your Perplexity API key and configuration.
Uses the exact same code pattern as the working example.
"""
import os
import sys
from dotenv import load_dotenv

# Hardcoded API key (same as user's working code)
PERPLEXITY_API_KEY = "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"

# Try to import Perplexity SDK
try:
    from perplexity import Perplexity
    PERPLEXITY_SDK_AVAILABLE = True
except ImportError:
    PERPLEXITY_SDK_AVAILABLE = False
    print("⚠️  Perplexity SDK not installed. Install with: pip install perplexity")
    sys.exit(1)

def search(query):
    """Search function using exact same code pattern as working example."""
    from perplexity import Perplexity
    
    client = Perplexity(api_key=PERPLEXITY_API_KEY)
    
    print("\nSearching...\n")
    search = client.search.create(
        query=query,
        max_results=5,
        max_tokens_per_page=1024
    )
    
    print(f"Found {len(search.results)} results:\n")
    for i, result in enumerate(search.results, 1):
        print(f"{i}. {result.title}")
        print(f"   URL: {result.url}")
        if hasattr(result, 'snippet') and result.snippet:
            print(f"   Snippet: {result.snippet[:150]}...")
        if hasattr(result, 'date') and result.date:
            print(f"   Date: {result.date}")
        print()
    
    return search


def test_perplexity_api():
    """Test Perplexity API connection and search functionality."""
    
    print("=" * 60)
    print("Perplexity API Test")
    print("=" * 60)
    print(f"\nAPI Key Present: {'Yes' if PERPLEXITY_API_KEY else 'No'}")
    
    if PERPLEXITY_API_KEY:
        # Show first and last 4 characters for verification (don't expose full key)
        masked_key = f"{PERPLEXITY_API_KEY[:4]}...{PERPLEXITY_API_KEY[-4:]}" if len(PERPLEXITY_API_KEY) > 8 else "***"
        print(f"API Key (masked): {masked_key}")
        print(f"API Key Length: {len(PERPLEXITY_API_KEY)} characters")
        print(f"SDK Available: {'Yes' if PERPLEXITY_SDK_AVAILABLE else 'No'}")
    else:
        print("\n❌ ERROR: PERPLEXITY_API_KEY not found in environment variables!")
        print("Please check your .env file and make sure it contains:")
        print("PERPLEXITY_API_KEY=your_actual_api_key_here")
        return False
    
    if not PERPLEXITY_SDK_AVAILABLE:
        print("\n❌ ERROR: Perplexity SDK not installed!")
        print("Install with: pip install perplexity")
        return False
    
    # Test using exact same code pattern as working example
    print("\n" + "=" * 60)
    print("Testing Perplexity Search (using exact working code pattern)...")
    print("=" * 60)
    
    try:
        test_query = "What is the capital of France?"
        print(f"\nTest Query: {test_query}")
        search_result = search(test_query)
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Your API key is valid and working!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    


if __name__ == "__main__":
    print("\nStarting Perplexity API test...\n")
    
    success = test_perplexity_api()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test completed successfully!")
        print("Your Perplexity API is configured correctly.")
    else:
        print("❌ Test failed!")
        print("Please fix the issues above and try again.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

