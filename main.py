import json
from pyrogram import Client
from scraper import *
from config import *
from database import *
import asyncio
from techzdl import TechZDL

database_name = "Spidydb"
db = connect_to_mongodb(DATABASE, database_name)
collection_name = COLLECTION_NAME


app = Client("Massify", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=10)




async def main():
    async with app:
        data = fetch_main()
        for item in data:
           print(f"URL: {item.get('url')}")
           if not check_db(db, collection_name, item.get('url')):
              for song in item.get("songs", []):
                 for download in song.get("download_links", []):
                      print(f"{song.get('name')} - Quality: {download.get('quality')} - {song.get('song_link')}")
                      print("Downloading....")
                      downloader = TechZDL(url=download.get('url'))
                      file_info = await downloader.get_file_info()
                      file_name = file_info['filename']
                      print(f"Filename: {file_info['filename']}")
                      print(f"Total Size: {file_info['total_size']} bytes")
                      await downloader.start()
                      caption = "Metadata: \n"
                      movie_info = item.get("movie_info", {})
                      for key, value in movie_info.items():
                           caption+= f"{key}: {value}\n"
                      await app.send_audio(DUMP_ID,audio=file_name,caption=caption)
                      result = item
                      insert_document(db, collection_name, result)
                        


        


if __name__ == "__main__":
    logging.info("Music Bot Started...")
    app.run(main())
