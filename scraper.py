import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import urljoin
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('music_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SongDownloadScraper:
    """
    A web scraper for downloading music from MassTamilan website
    """
    BASE_URL = "https://masstamilan.dev"

    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize the scraper with a custom user agent
        
        :param user_agent: Optional custom user agent string
        """
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch_links(self, url: str) -> List[Dict[str, str]]:
        """
        Fetch song download links from a given URL
        
        :param url: URL to scrape
        :return: List of song details with download links
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            songs = []
            
            for index, tr in enumerate(soup.find_all('tr', attrs={'itemprop': 'itemListElement'}), 1):
                # Find song name
                name_link = tr.find('a', href=True, title=lambda x: x and 'Download' in x)
                
                # Find download links with 'dlink anim' class
                download_links = tr.find_all('a', class_='dlink anim')
                
                if name_link and download_links:
                    song_details = {
                        'name': name_link.text.strip(),
                        'song_link': urljoin(self.BASE_URL, name_link['href']),
                        'download_links': [
                            {
                                'quality': link.text.strip(),
                                'url': urljoin(self.BASE_URL, link['href'])
                            } for link in download_links
                        ]
                    }
                    songs.append(song_details)
                    self.logger.info(f"Processed song: {song_details['name']}")
            
            return songs
        
        except requests.RequestException as e:
            self.logger.error(f"Error fetching URL {url}: {e}")
            return []

def extract_movie_info(url: str) -> Dict[str, str]:
    """
    Extract movie information from a given URL
    
    :param url: URL of the movie page
    :return: Dictionary of movie details
    """
    logger = logging.getLogger('extract_movie_info')
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract poster caption
        poster_caption = soup.find('figcaption', class_='cen')
        poster_caption_text = poster_caption.text.strip() if poster_caption else "N/A"
        
        # Extract movie details from fieldset
        fieldset = soup.find('fieldset', id='movie-handle')
        if not fieldset:
            logger.warning(f"No movie details found for URL: {url}")
            return {}

        # Helper function to safely extract text
        def safe_extract(finder, default="N/A"):
            try:
                return finder().text.strip()
            except (AttributeError, TypeError):
                return default

        movie_info = {
            "Poster Caption": poster_caption_text,
            "Starring": safe_extract(lambda: fieldset.find('a', href=lambda x: x and '/artist/' in x)),
            "Music": safe_extract(lambda: fieldset.find('a', href=lambda x: x and '/music/' in x)),
            "Director": safe_extract(lambda: fieldset.find('b', string="Director:").next_sibling),
            "Lyricists": safe_extract(lambda: fieldset.find('b', string="Lyricists:").next_sibling),
            "Year": safe_extract(lambda: fieldset.find('a', href=lambda x: x and '/browse-by-year/' in x)),
            "Language": safe_extract(lambda: fieldset.find('a', href=lambda x: x and '/tamil-songs' in x)),
            "First Released": safe_extract(lambda: fieldset.find('b', string="Fist Released on MassTamilan:").next_sibling),
            "Last Updated": safe_extract(lambda: fieldset.find('b', string="Last Updated on MassTamilan:").next_sibling)
        }

        logger.info(f"Successfully extracted movie info for URL: {url}")
        return movie_info

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for URL {url}: {e}")
        return {}

def scrape_index(page: int) -> List[str]:
    """
    Scrape the index page for music links
    
    :param page: Page number to scrape
    :return: List of music URLs
    """
    logger = logging.getLogger('scrape_index')
    try:
        url = f"https://masstamilan.dev/tamil-songs?page={page}"
        scraper = SongDownloadScraper()
        
        response = requests.get(url, headers=scraper.headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        
        # Extract music page URLs, skipping the first 6 links
        index_links = ["https://masstamilan.dev" + link.get('href') for link in links if link.get('href')][6:16]
        
        results = []
        for music_url in index_links:
            try:
                # Fetch song links and movie info
                song_links = scraper.fetch_links(music_url)
                movie_info = extract_movie_info(music_url)
                
                results.append({
                    'url': music_url,
                    'songs': song_links,
                    'movie_info': movie_info
                })
                
                # Add a small delay to be respectful to the server
                time.sleep(1)
            
            except Exception as e:
                logger.error(f"Error processing {music_url}: {e}")
        
        logger.info(f"Scraped {len(results)} links from page {page}")
        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"Error scraping index page {page}: {e}")
        return []

def main():
    """
    Main function to run the scraper
    """
    logger = logging.getLogger('main')
    all_results = []
    
    try:
        for page in range(1, 5):
            page_results = scrape_index(page)
            all_results.extend(page_results)
        
        # Optional: Save results to a file or process further
        with open('data.json', 'w') as f:
            json.dump(all_results, f)
        logger.info(f"Total results collected: {len(all_results)}")
        return all_results
    
    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}")

if __name__ == "__main__":
    main()
