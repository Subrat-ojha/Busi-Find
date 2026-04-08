import os
from dotenv import load_dotenv

load_dotenv()

# API Keys (optional - each enables its respective source)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
YELP_API_KEY = os.getenv("YELP_API_KEY", "")
FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY", "")

# Search defaults
DEFAULT_RADIUS_METERS = 5000  # 5 km
DEFAULT_LIMIT = 50

# Website checker
REQUEST_TIMEOUT = 5  # seconds
MAX_WORKERS = 10  # concurrent website checks

# Rate limiting (seconds between requests)
SCRAPE_DELAY = 2
