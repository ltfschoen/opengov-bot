import asyncio
import aiohttp
import logging
import os
import re
from bot.utils.data_processing import CacheManager
from bot.utils.subquery import SubstrateAPI
from typing import Dict

class OpenGovernance2:
    def __init__(self, config, substrate=None):
        self.config = config
        self.util = CacheManager
        self.substrate = substrate
        self.logger = logging.getLogger(__name__)

    @staticmethod
    async def fetch_referendum_data(referendum_id: int, network: str):
        """
        Fetches referendum data from a set of URLs using a given referendum ID and network name.

        The function makes HTTP GET requests to each URL in the list. If a response is successful
        and the JSON response contains a non-empty 'title', the function will immediately return
        that response without checking the remaining URLs. If none of the responses are successful,
        the function returns a default response indicating that the referendum details could not
        be retrieved.

        Parameters:
        referendum_id (int): The ID of the referendum to fetch data for.
        network (str): The name of the network where the referendum is held. This is used to
                       construct the URLs and to set the 'x-network' header in the HTTP requests.

        Returns:
        dict: A dictionary containing the referendum data. This dictionary includes a 'title' key,
              a 'content' key, and a 'successful_url' key. If no successful response is received
              from any of the URLs, the 'title' will be 'None', the 'content' will be a message
              indicating that the details could not be retrieved, and the 'successful_url' will be
              None. Otherwise, the returned dictionary will be the successful JSON response from
              one of the URLs, with a 'successful_url' key added to indicate which URL the
              response came from.
        """
        urls = [
            f"https://api.polkassembly.io/api/v1/posts/on-chain-post?postId={referendum_id}&proposalType=referendums_v2",
            f"https://{network}.subsquare.io/api/gov2/referendums/{referendum_id}",
        ]

        headers = {"x-network": network}
        successful_response = None
        successful_url = None

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    # Make the request separately and use async with for the response
                    response = await asyncio.wait_for(session.get(url, headers=headers), timeout=60)

                    async with response:
                        response.raise_for_status()
                        json_response = await response.json()

                        # Add 'title' key if it doesn't exist
                        if "title" not in json_response.keys():
                            json_response["title"] = "None"

                        # Check if 'title' is not None or empty string
                        if json_response["title"] not in {None, "None", ""}:
                            successful_response = json_response
                            successful_url = url
                            # Once a successful response is found, no need to continue checking other URLs
                            break

                except asyncio.TimeoutError:
                    logging.error(f"Request to {url} timed out.")
                except aiohttp.ClientResponseError as http_error:
                    logging.error(f"HTTP exception occurred while accessing {url}: {http_error}")
                    logging.error(f"Retrying on {urls[1]}")

        if successful_response is None:
            return {"title": "None",
                    "content": "Unable to retrieve details from both sources",
                    "successful_url": None}
        else:
            successful_response["successful_url"] = successful_url
            return successful_response

    async def check_referendums(self, network_name: str, substrate_api: SubstrateAPI) -> Dict:
        """
        Check for new referendums and return the new ones.

        Args:
            network_name (str): The name of the network to check.
            substrate_api (SubstrateAPI): The substrate API instance to use.

        Returns:
            Dict: A dictionary containing the new referendums.
        """
        try:
            import time
            overall_start = time.time()

            # Use just the filename, not the path with 'data/' prefix
            cache_filename = 'governance.cache'
            print(f"DEBUG: Using cache filename: {cache_filename}")

            # Get ongoing referendums
            print(f"DEBUG: Starting referendumInfoFor() at {time.time() - overall_start:.4f}s")
            referendum_info = await substrate_api.referendumInfoFor()
            print(f"DEBUG: Completed referendumInfoFor() at {time.time() - overall_start:.4f}s")

            # Get the data directory and full path to cache file
            data_dir = CacheManager.get_data_dir()
            full_path = os.path.join(data_dir, cache_filename)

            # Load the cached data directly to compare with blockchain data
            print(f"DEBUG: Starting cache load at {time.time() - overall_start:.4f}s")
            cached_data = {}
            if os.path.exists(full_path):
                cached_data = CacheManager.load_data_from_cache(full_path)
                print(f"DEBUG: Loaded {len(cached_data)} referenda from cache")
            print(f"DEBUG: Completed cache load at {time.time() - overall_start:.4f}s")

            # Dictionary to store new referendums
            new_referendums = {}

            # First, check for items in blockchain data that don't exist in cache
            # This handles the case where entries were manually deleted from the cache
            print(f"DEBUG: Starting direct comparison at {time.time() - overall_start:.4f}s")
            for ref_id, ref_data in referendum_info.items():
                if ref_id not in cached_data:
                    print(f"DEBUG: Found referendum #{ref_id} in blockchain data but not in cache")
                    new_referendums[ref_id] = ref_data
            print(f"DEBUG: Completed direct comparison at {time.time() - overall_start:.4f}s")

            # Now use DeepDiff to check for any other changes
            print(f"DEBUG: Starting DeepDiff at {time.time() - overall_start:.4f}s")
            results = CacheManager.get_cache_difference(cache_filename, referendum_info)
            print(f"DEBUG: Cache difference results: {results}")
            print(f"DEBUG: Completed DeepDiff at {time.time() - overall_start:.4f}s")

            # Process the DeepDiff results
            if results and 'dictionary_item_added' in results:
                for item in results['dictionary_item_added']:
                    # Extract the index from the item string (format: "root['123']")
                    index_match = re.search(r"root\['(\d+)'\]", item)
                    if index_match:
                        index = index_match.group(1)
                        # Only add if not already added from direct comparison
                        if index not in new_referendums and index in referendum_info:
                            new_referendums[index] = referendum_info[index]

            # Save the updated data to cache AFTER we've detected differences
            print(f"DEBUG: Starting cache save at {time.time() - overall_start:.4f}s")
            CacheManager.save_data_to_cache(full_path, referendum_info)
            print(f"DEBUG: Completed cache save at {time.time() - overall_start:.4f}s")

            print(f"DEBUG: referendum_info contains {len(referendum_info)} referenda")
            print(f"DEBUG: new_referendums contains {len(new_referendums)} referenda: {list(new_referendums.keys())}")
            print(f"DEBUG: Total check_referendums time: {time.time() - overall_start:.4f}s")

            return new_referendums

        except Exception as e:
            self.logger.error(f"Error checking referendums: {e}")
            print(f"ERROR:root:Error checking referendums: {e}")
            raise
