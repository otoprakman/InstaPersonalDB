import json
import os
import instaloader
from pathlib import Path

def load_shortcodes(path):
    """
    Parses the user provided JSON(s) to extract shortcodes.
    Accepts a file path or a directory path.
    """
    path_obj = Path(path)
    if path_obj.is_dir():
        files = list(path_obj.glob("*.json"))
    else:
        files = [path_obj]
        
    shortcodes = []
    
    for json_path in files:
        if not json_path.exists():
            continue
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            posts_list = []
            if isinstance(data, dict):
                # Try to find list in known keys
                if 'saved_saved_media' in data:
                    posts_list.extend(data['saved_saved_media'])
                if 'saved_saved_collections' in data:
                    posts_list.extend(data['saved_saved_collections'])
                
                # If no known keys found, check if it looks like a single item or unknown list
                if not posts_list:
                    if 'string_map_data' in data:
                        posts_list.append(data)
            elif isinstance(data, list):
                posts_list = data

            for item in posts_list:
                if not isinstance(item, dict):
                    continue

                # 1. Try 'string_map_data' -> 'Shortcode' -> 'value' (saved_media format)
                if 'string_map_data' in item:
                    # Case A: Explicit Shortcode
                    shortcode = item['string_map_data'].get('Shortcode', {}).get('value')
                    if shortcode:
                        shortcodes.append(shortcode)
                        continue
                    
                    # Case B: Name -> href (collections format)
                    href = item['string_map_data'].get('Name', {}).get('href')
                    if href:
                        # expected: https://www.instagram.com/reel/C0ZlFU_Ndua/
                        parts = href.strip('/').split('/')
                        for marker in ['p', 'reel', 'reels', 'tv']:
                            if marker in parts:
                                idx = parts.index(marker)
                                if len(parts) > idx + 1:
                                    shortcodes.append(parts[idx+1])
                                    break
                        continue # Found or not, we processed this item via string_map_data

                # 2. Fallback: direct keys
                if 'shortcode' in item:
                    shortcodes.append(item['shortcode'])
                elif 'link' in item:
                    # https://www.instagram.com/p/Cz7.../
                    url = item['link']
                    parts = url.strip('/').split('/')
                    for marker in ['p', 'reel', 'reels', 'tv']:
                        if marker in parts:
                            idx = parts.index(marker)
                            if len(parts) > idx + 1:
                                shortcodes.append(parts[idx+1])
                                break
                                
        except Exception as e:
            print(f"Error parsing {json_path}: {e}")
            
    return list(set(shortcodes)) # Unique

def download_post(shortcode, target_dir="data/raw"):
    """
    Downloads a post by shortcode using Instaloader.
    Saves to data/raw/{shortcode}
    """
    # Ensure target directory exists
    raw_dir = Path(target_dir).resolve()
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize Instaloader
    L = instaloader.Instaloader(
        download_pictures=True,
        download_videos=True, 
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=True,
        compress_json=False
    )
    
    print(f"Downloading post: {shortcode}")
    
    # Change CWD to target_dir so instaloader creates the folder there
    original_cwd = os.getcwd()
    try:
        os.chdir(raw_dir)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=shortcode)
        return True
    except Exception as e:
        print(f"Failed to download {shortcode}: {e}")
        return False
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        codes = load_shortcodes(sys.argv[1])
        print(f"Found {len(codes)} shortcodes.")
        for code in codes[:3]: # Test first 3
            download_post(code)
