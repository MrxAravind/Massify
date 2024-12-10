import json
from pyrogram import Client
from scraper import *
from config import *
from database import *
import os
import subprocess
import tempfile
import asyncio

database_name = "Spidydb"
db = connect_to_mongodb(DATABASE, database_name)
collection_name = COLLECTION_NAME


app = Client("Massify", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=10)




def download_with_aria2c(url, output_dir=None, filename=None):
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        'aria2c',  # aria2c command
        url,  # URL to download
        '-d', output_dir,  # Destination directory
        '--max-concurrent-downloads=1',  # Limit to 1 download
        '--max-connection-per-server=5',  # Optimize download
        '--min-split-size=1M',  # Minimum split size
        '--allow-overwrite=true'  # Allow overwriting existing files
    ]
    if filename:
        cmd.extend(['-o', filename])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if filename:
            downloaded_file = os.path.join(output_dir, filename)
        else:
            # Attempt to find the downloaded file in the output directory
            downloaded_files = os.listdir(output_dir)
            if not downloaded_files:
                raise RuntimeError("No file was downloaded")
            downloaded_file = os.path.join(output_dir, downloaded_files[0])
        if not os.path.exists(downloaded_file) or os.path.getsize(downloaded_file) == 0:
            raise RuntimeError("Download failed or resulted in an empty file")
        
        return downloaded_file
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Download failed. Error: {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"An error occurred during download: {str(e)}")
 
async def main():
    async with app:
        try:
             data = fetch_main()
             for item in data:
                  print(f"URL: {item.get('url')}")
                  if not check_db(db, collection_name, item.get('url')):
                      for song in item.get("songs", []):
                           for download in song.get("download_links", []):
                               print(f"{song.get('name')} - Quality: {download.get('quality')} - {song.get('song_link')}")
                               print("Downloading....")
                               file_path = download_with_aria2c(download.get('url'))
                               print(f"File downloaded successfully to: {file_path}")
                               caption = "Metadata: \n"
                               movie_info = item.get("movie_info", {})
                               for key, value in movie_info.items():
                                    caption+= f"{key}: {value}\n"
                               thumb = f"{song.get('name')}thumb.png"
                               os.system(f"""ffmpeg -i {file_path} -an -c:v copy "{thumb}" > ffmpeglog.txt """)
                               await app.send_photo(DUMP_ID,photo=thumb,caption=caption)
                               await app.send_document(DUMP_ID,document=file_path,thumb=thumb)
                               result = item
                               insert_document(db, collection_name, result)
                               os.remove()
                               
        except Exception as e:
               print(f"Download error: {e}")
    
        


if __name__ == "__main__":
    logging.info("Music Bot Started...")
    app.run(main())
