import os
import json
import asyncio
import logging
import tempfile
import subprocess
from typing import Dict, List, Optional

import pyrogram
from pymongo import MongoClient
from pyrogram import Client

# Improved configuration management
from config import (
    API_ID, API_HASH, BOT_TOKEN, 
    DATABASE, COLLECTION_NAME, DUMP_ID
)
from scraper import fetch_main
from database import connect_to_mongodb, check_db, insert_document

class MusicDownloader:
    def __init__(self, 
                 database_name: str = "Spidydb", 
                 max_retry_attempts: int = 3, 
                 download_timeout: int = 300):
        """
        Initialize the Music Downloader with configurable parameters
        
        Args:
            database_name (str): Name of the MongoDB database
            max_retry_attempts (int): Maximum number of download retry attempts
            download_timeout (int): Timeout for downloads in seconds
        """
        self.db = connect_to_mongodb(DATABASE, database_name)
        self.collection_name = COLLECTION_NAME
        self.app = Client(
            "Massify", 
            api_id=API_ID, 
            api_hash=API_HASH, 
            bot_token=BOT_TOKEN, 
            workers=10
        )
        self.max_retry_attempts = max_retry_attempts
        self.download_timeout = download_timeout
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def download_with_aria2c(
        self, 
        url: str, 
        output_dir: Optional[str] = None, 
        filename: Optional[str] = None
    ) -> str:
        """
        Download file using aria2c with enhanced error handling and flexibility
        
        Args:
            url (str): URL of the file to download
            output_dir (Optional[str]): Directory to save downloaded file
            filename (Optional[str]): Specific filename for the download
        
        Returns:
            str: Path to the downloaded file
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            'aria2c',
            url,
            '-d', output_dir,
            '--max-concurrent-downloads=1',
            '--max-connection-per-server=5',
            '--min-split-size=1M',
            '--allow-overwrite=true',
            '--timeout=30',  # Added connection timeout
            '--connect-timeout=10'
        ]
        
        if filename:
            cmd.extend(['-o', filename])
        
        for attempt in range(self.max_retry_attempts):
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=self.download_timeout,
                    check=True
                )
                
                downloaded_files = os.listdir(output_dir)
                if not downloaded_files:
                    raise RuntimeError("No file was downloaded")
                
                downloaded_file = os.path.join(output_dir, downloaded_files[0])
                
                if not os.path.exists(downloaded_file) or os.path.getsize(downloaded_file) == 0:
                    raise RuntimeError("Download failed or resulted in an empty file")
                
                return downloaded_file
            
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                self.logger.warning(f"Download attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retry_attempts - 1:
                    raise RuntimeError(f"Download failed after {self.max_retry_attempts} attempts")
    
    async def process_song(self, song: Dict, app: Client, dump_id: int) -> None:
        """
        Process and upload a single song
        
        Args:
            song (Dict): Song metadata dictionary
            app (Client): Pyrogram client instance
            dump_id (int): Telegram dump channel/group ID
        """
        for download in song.get("download_links", []):
            try:
                file_path = self.download_with_aria2c(download.get('url'))
                
                # Generate thumbnail
                thumb = f"{song.get('name')}_thumb.png"
                subprocess.run([
                    "ffmpeg", 
                    "-i", file_path, 
                    "-an", 
                    "-c:v", "copy", 
                    thumb
                ], check=True)
                
                # Prepare captions
                movie_caption = "Metadata:\n" + "\n".join(
                    f"{k}: {v}" for k, v in song.get("movie_info", {}).items()
                )
                song_caption = f"{song.get('name')}\nQuality: {download.get('quality')}"
                
                # Upload thumbnail
                await app.send_photo(
                    dump_id, 
                    photo=thumb, 
                    caption=movie_caption
                )
                
                # Upload song
                await app.send_document(
                    dump_id, 
                    document=file_path, 
                    caption=song_caption, 
                    thumb=thumb
                )
                
                # Clean up temporary files
                os.remove(file_path)
                os.remove(thumb)
                
            except Exception as e:
                self.logger.error(f"Error processing song {song.get('name')}: {e}")

    async def main(self):
        """
        Main async method to scrape, download, and upload songs
        """
        async with self.app:
            page = 1
            while True:
                try:
                    data = fetch_main(page)
                    if len(data) != 10:
                        self.logger.info("Reached end of pages. Waiting 1 hour...")
                        await asyncio.sleep(3600)
                        page = 1
                        continue

                    for item in data:
                        if not check_db(self.db, self.collection_name, item.get('url')):
                            # Process songs in parallel
                            await asyncio.gather(*(
                                self.process_song(song, self.app, DUMP_ID) 
                                for song in item.get("songs", [])
                            ))
                            
                            # Insert processed item to database
                            insert_document(self.db, self.collection_name, item)
                            page += 1

                except Exception as e:
                    self.logger.error(f"Processing error on page {page}: {e}")
                    await asyncio.sleep(60)  # Wait before retry

def main():
    """Entry point for the script"""
    downloader = MusicDownloader()
    downloader.app.run(downloader.main())

if __name__ == "__main__":
    main()
