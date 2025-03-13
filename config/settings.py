import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

TOKEN_API_URL = "https://api.mainnet.myonion.fun/api/token"
ALPH_PRICE_API = "https://api.coingecko.com/api/v3/simple/price?ids=alephium&vs_currencies=usd"
DEFAULT_SUPPLY = 1_000_000_000  # 1 billion

