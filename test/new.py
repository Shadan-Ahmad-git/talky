import os

PERPLEXITY_API_KEY = "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"

def search(query):
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

def main():
    print("=== Perplexity Web Search ===")
    print("Enter your search query (or 'quit' to exit)\n")
    
    while True:
        query = input("Search query: ").strip()
        
        if query.lower() == 'quit':
            print("Exiting...")
            break
        
        if not query:
            print("Please enter a valid query.\n")
            continue
        
        try:
            search(query)
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()
