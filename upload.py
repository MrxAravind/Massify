import json
from pyrogram import Client
from scraper import *

app = Client("Massify", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=10)



def print_structure(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    for item in data:
        print(f"URL: {item.get('url')}")
        print("Songs:")
        for song in item.get("songs", []):
            print(f"  - Name: {song.get('name')}")
            print(f"    Song Link: {song.get('song_link')}")
            print("    Download Links:")
            for download in song.get("download_links", []):
                print(f"      Quality: {download.get('quality')}")
                print(f"      URL: {download.get('url')}")
        print("Movie Info:")
        movie_info = item.get("movie_info", {})
        for key, value in movie_info.items():
            print(f"  {key}: {value}")
        print("=" * 40)


if __name__ == "__main__":
    logging.info("Bot Started...")
    app.run(main())
