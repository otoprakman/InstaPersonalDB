import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.ingest import load_shortcodes, download_post
from src.processor import process_pipeline
from src.rag_db import ingest_document, query_similar

def test_pipeline():
    print("=== Testing Pipeline ===")
    
    # 1. Ingest
    json_path = "saved_posts_sample.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} missing")
        return
        
    print(f"Loading {json_path}...")
    shortcodes = load_shortcodes(json_path)
    print(f"Shortcodes found: {shortcodes}")
    
    if not shortcodes:
        print("No shortcodes found. Exiting.")
        return

    # Process first one
    code = shortcodes[0]
    
    print(f"Downloading {code}...")
    success = download_post(code)
    
    if not success:
        print("Download failed (might be private post or issues).")
        # Continue if folder exists anyway (maybe previous run)
    
    print(f"Processing {code}...")
    result = process_pipeline(code)
    
    if result:
        print("--- Result Content ---")
        print(result['content'][:200] + "...")
        print("----------------------")
        
        print(f"Ingesting {code}...")
        ingest_document(result['shortcode'], result['content'], result['image_path'])
        
        print("Querying 'movie'...")
        q_res = query_similar("movie")
        print("Query Ids:", q_res['ids'])
    else:
        print("Processing returned None.")

if __name__ == "__main__":
    test_pipeline()
