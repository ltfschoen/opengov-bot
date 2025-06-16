"""
Price utility functions for fetching cryptocurrency prices from various APIs.
Supports both single-network and multi-network bot configurations.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional, Union
from bot.utils.logger import Logger

logger = Logger()

# Network to symbol mapping
NETWORK_SYMBOL_MAP = {
    'polkadot': 'DOT',
    'kusama': 'KSM',
    'westend': 'WND',
    # Add more networks as needed
}

class PriceAPI:
    """Base class for price API implementations"""
    def __init__(self):
        self.prices = {}

    def get_price(self, symbol: str) -> Optional[float]:
        """Get price for a symbol"""
        return self.prices.get(symbol)

    def update_prices(self):
        """Update price cache is to be implemented by subclasses"""
        pass

class BinanceAPI(PriceAPI):
    """Binance price API implementation"""
    def __init__(self):
        super().__init__()
        self.update_prices()

    def update_prices(self):
        """Update prices from Binance API"""
        try:
            response = requests.get('https://api.binance.com/api/v3/ticker/price')
            if response.status_code == 200:
                data = response.json()
                # Process USDT pairs
                for item in data:
                    if item['symbol'].endswith('USDT'):
                        symbol = item['symbol'].replace('USDT', '')
                        self.prices[symbol] = float(item['price'])
                logger.info(f"Updated {len(self.prices)} prices from Binance")
            else:
                logger.error(f"Failed to fetch Binance prices: {response.status_code}")
        except Exception as e:
            logger.error(f"Error updating Binance prices: {e}")

class CoinmarketcapAPI(PriceAPI):
    """CoinMarketCap API implementation"""
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        if api_key:
            self.update_prices()

    def update_prices(self):
        """Update prices from CoinMarketCap API"""
        if not self.api_key:
            logger.warning("No CoinMarketCap API key provided")
            return

        try:
            headers = {
                'X-CMC_PRO_API_KEY': self.api_key,
            }
            response = requests.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest',
                headers=headers,
                params={'limit': 100})
            if response.status_code == 200:
                data = response.json()
                for item in data.get('data', []):
                    symbol = item['symbol']
                    self.prices[symbol] = item['quote']['USD']['price']
                logger.info(f"Updated {len(self.prices)} prices from CoinMarketCap")
            else:
                logger.error(f"Failed to fetch CoinMarketCap prices: {response.status_code}")
        except Exception as e:
            logger.error(f"Error updating CoinMarketCap prices: {e}")

class CoinGeckoAPI(PriceAPI):
    """CoinGecko API implementation with retry logic"""
    def __init__(self):
        super().__init__()
        self.update_prices()

    def get_asset_price(self, asset_id: str, currencies: str = 'usd') -> float:
        """
        Fetches price of an asset from the CoinGecko API.

        Args:
            asset_id (str): ID of the asset (e.g., "polkadot")
            currencies (str): Comma-separated currency symbols (default: 'usd')

        Returns:
            float: Price in the specified currency or 0 if not found
        """
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset_id}&vs_currencies={currencies}"
        logger.info(f"Fetching price from CoinGecko for {asset_id}")

        retry_strategy = Retry(
            total=3,             # Retry up to 3 times
            backoff_factor=3,    # Wait 3 seconds between retries
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("https://", adapter)

        try:
            response = http.get(url)
            response.raise_for_status()
            data = response.json()

            if asset_id not in data:
                logger.warning(f"Asset ID '{asset_id}' not found in CoinGecko")
                return 0

            price = data[asset_id].get('usd', 0)
            logger.info(f"Price for '{asset_id}' is ${price}")
            return price

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error occurred: {e}")
        except Exception as e:
            logger.error(f"Error fetching price from CoinGecko: {e}")

        return 0

    def update_prices(self):
        """Update common cryptocurrency prices"""
        try:
            # Get prices for top cryptocurrencies
            top_coins = "polkadot,kusama"
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={top_coins}&vs_currencies=usd"

            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                # Map CoinGecko IDs to symbols
                id_to_symbol = {
                    "polkadot": "DOT",
                    "kusama": "KSM"
                }

                for coin_id, price_data in data.items():
                    symbol = id_to_symbol.get(coin_id)
                    if symbol:
                        self.prices[symbol] = price_data.get('usd', 0)

                logger.info(f"Updated {len(self.prices)} prices from CoinGecko")
            else:
                logger.error(f"Failed to fetch CoinGecko prices: {response.status_code}")
        except Exception as e:
            logger.error(f"Error updating CoinGecko prices: {e}")

# Initialize price APIs
binance_api = BinanceAPI()
coingecko_api = CoinGeckoAPI()

def get_asset_price_v1(asset: str) -> float:
    """
    Get asset price from Binance API.

    Args:
        asset (str): Asset symbol (e.g., 'DOT', 'KSM')

    Returns:
        float: Price in USD or 0 if not found
    """
    try:
        if asset in binance_api.prices:
            return binance_api.prices[asset]
    except Exception as error:
        logger.error(f"Error getting asset price from Binance: {error}")
    return 0

def get_asset_price_v2(asset_id: str) -> float:
    """
    Get asset price using available price APIs.
    Maps network name to asset symbol if needed.

    Args:
        asset_id (str): Asset symbol or network ID (e.g., 'DOT', 'polkadot')

    Returns:
        float: Price in USD or 0 if not found
    """
    # Map network name to symbol if applicable
    symbol = NETWORK_SYMBOL_MAP.get(asset_id.lower(), asset_id)

    # Try Binance first (fastest)
    try:
        if symbol in binance_api.prices:
            return binance_api.prices[symbol]
    except Exception:
        pass

    # Try CoinGecko next
    try:
        # Use cached prices for common symbols
        if symbol in coingecko_api.prices:
            return coingecko_api.prices[symbol]

        # Try direct API call for other assets
        # Map symbol back to CoinGecko ID if needed
        gecko_id = asset_id.lower()  # Default to lowercase asset_id
        price = coingecko_api.get_asset_price(gecko_id)
        if price > 0:
            return price
    except Exception as error:
        logger.error(f"Error getting {symbol} price from CoinGecko: {error}")

    return 0

def update_all_prices():
    """Update prices from all available APIs"""
    binance_api.update_prices()
    coingecko_api.update_prices()
