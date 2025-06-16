import asyncio
import json
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timezone

from bot.utils.logger import Logger
from bot.utils.gov2 import OpenGovernance2
from bot.utils.subquery import SubstrateAPI
from bot.utils.data_processing import CacheManager
from bot.utils.network_manager import NetworkManager

class MultiNetworkHandler:
    """
    Handles operations across multiple blockchain networks simultaneously,
    allowing for parallel processing of governance data.
    """
    def __init__(self, network_manager: NetworkManager):
        """
        Initialize handler with a network manager.

        Args:
            network_manager: NetworkManager instance to use for network configurations
        """
        self.network_manager = network_manager
        self.logger = Logger()
        self.network_apis = {}  # Store SubstrateAPI instances by network ID
        self.network_opengov = {}  # Store OpenGovernance2 instances by network ID

    async def initialize_connections(self):
        """Initialize connections to all enabled networks."""
        networks = await self.network_manager.get_all_networks()

        # Create SubstrateAPI and OpenGovernance2 instances for each network
        for network_id, network_config in networks.items():
            # Convert network config to a compatible format for SubstrateAPI
            substrate_config = type('Config', (), {
                'SUBSTRATE_WSS': network_config['substrate_wss'],
                'NETWORK_NAME': network_config['network_name'],
                'PEOPLE_WSS': network_config.get('people_wss'),
                'SYMBOL': network_config['symbol'],
                'TOKEN_DECIMAL': network_config['token_decimal'],
                # Add other required config fields with defaults
                'PROXIED_ADDRESS': network_config.get('proxied_address', ''),
                'PROXY_ADDRESS': network_config.get('proxy_address', ''),
                'MNEMONIC': network_config.get('mnemonic', ''),
            })

            try:
                substrate_api = SubstrateAPI(substrate_config)
                self.network_apis[network_id] = substrate_api
                self.network_opengov[network_id] = OpenGovernance2(substrate_config, substrate_api)
                self.logger.info(f"Initialized connection for network: {network_id}")
            except Exception as e:
                self.logger.error(f"Failed to initialize connection for network {network_id}: {e}")

    async def close_connections(self):
        """Close all network connections."""
        for network_id, substrate_api in self.network_apis.items():
            try:
                await substrate_api.close()
                self.logger.info(f"Closed connection for network: {network_id}")
            except Exception as e:
                self.logger.error(f"Error closing connection for network {network_id}: {e}")

    async def check_all_referendums(self) -> Dict[str, Dict]:
        """
        Check for new referenda across all networks in parallel.

        Returns:
            Dict mapping network_id to a tuple of (new_referendums, referendum_info)
        """
        tasks = []
        network_ids = []

        # Create tasks for each network
        for network_id, opengov in self.network_opengov.items():
            network_ids.append(network_id)
            tasks.append(opengov.check_referendums())

        # Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        referendum_data = {}
        for i, result in enumerate(results):
            network_id = network_ids[i]

            if isinstance(result, Exception):
                self.logger.error(f"Error checking referendums for {network_id}: {result}")
                referendum_data[network_id] = (False, None)
            else:
                new_referendums, referendum_info = result
                referendum_data[network_id] = (new_referendums, referendum_info)

                if new_referendums:
                    self.logger.info(f"Found {len(new_referendums)} new referenda for {network_id}")
                else:
                    self.logger.info(f"No new referenda found for {network_id}")

        return referendum_data

    async def get_network_data_by_referendum_id(self, ref_id: int, thread_id: int) -> Optional[Tuple[str, dict]]:
        """
        Get network ID and referendum data for a given referendum ID and thread ID.

        Args:
            ref_id: Referendum ID
            thread_id: Discord thread ID

        Returns:
            Tuple of (network_id, referendum_data) or None if not found
        """
        # Load vote counts from file
        try:
            with open('../data/vote_counts.json', 'r') as f:
                vote_counts = json.load(f)

            # Search for thread ID and check if network matches
            for network_id in vote_counts.keys():
                for ref_index, ref_data in vote_counts.get(network_id, {}).items():
                    if (ref_index == str(ref_id) and
                        ref_data.get('thread_id') == thread_id):
                        return network_id, ref_data

            return None
        except Exception as e:
            self.logger.error(f"Error getting network data for referendum {ref_id}: {e}")
            return None

    async def get_substrate_api(self, network_id: str) -> Optional[SubstrateAPI]:
        """Get SubstrateAPI instance for a specific network."""
        return self.network_apis.get(network_id)

    async def save_vote_counts(self, network_id: str, referendum_id: str,
                               thread_id: int, data: dict):
        """
        Save referendum data to vote_counts.json file.

        Args:
            network_id: Network identifier
            referendum_id: Referendum ID (as string)
            thread_id: Discord thread ID
            data: Referendum data to save
        """
        try:
            # Load current data
            with open('../data/vote_counts.json', 'r') as f:
                vote_counts = json.load(f)

            # Initialize network if not exists
            if network_id not in vote_counts:
                vote_counts[network_id] = {}

            # Add or update referendum data
            if referendum_id not in vote_counts[network_id]:
                vote_counts[network_id][referendum_id] = {}

            # Update with new data
            vote_counts[network_id][referendum_id].update(data)
            vote_counts[network_id][referendum_id]['thread_id'] = thread_id

            # Save back to file
            with open('../data/vote_counts.json', 'w') as f:
                json.dump(vote_counts, f, indent=4)

            self.logger.info(f"Updated vote counts for {network_id} referendum {referendum_id}")
        except Exception as e:
            self.logger.error(f"Error saving vote counts for {network_id} referendum {referendum_id}: {e}")

    async def get_vote_counts(self, network_id: str = None):
        """
        Get vote counts for a specific network or all networks.

        Args:
            network_id: Optional network ID to filter by

        Returns:
            Dict of vote counts
        """
        try:
            with open('../data/vote_counts.json', 'r') as f:
                vote_counts = json.load(f)

            if network_id:
                return vote_counts.get(network_id, {})
            return vote_counts
        except Exception as e:
            self.logger.error(f"Error loading vote counts: {e}")
            return {} if network_id else {}
