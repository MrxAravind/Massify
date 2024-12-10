from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.environ.get('API_ID', ''))
API_HASH = os.environ.get('API_HASH', '')
DATABASE = os.getenv("DATABASE")
DUMP_ID = int(os.environ.get('DUMP_ID', ''))
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
