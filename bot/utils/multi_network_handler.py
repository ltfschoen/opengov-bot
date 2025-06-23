import asyncio
import json
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timezone
import os
import time

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

        # Initialize Polkadot.js authentication only once if needed
        polkadot_auth_initialized = False
        use_polkadot_js = os.getenv('USE_POLKADOT_JS', 'false').lower() == 'true'

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
                # Set USE_POLKADOT_JS to False after the first initialization
                'USE_POLKADOT_JS': use_polkadot_js and not polkadot_auth_initialized,
            })

            try:
                substrate_api = SubstrateAPI(substrate_config)
                self.network_apis[network_id] = substrate_api
                self.network_opengov[network_id] = OpenGovernance2(substrate_config, substrate_api)
                self.logger.info(f"Initialized connection for network: {network_id}")
                
                # Mark Polkadot.js as initialized after the first network
                if use_polkadot_js and not polkadot_auth_initialized:
                    polkadot_auth_initialized = True
                    self.logger.info("Polkadot.js authentication initialized")
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

    async def check_all_referendums(self):
        """Check referendums for all networks in parallel."""
        import time
        overall_start = time.time()
        print(f"DEBUG: Starting check_all_referendums at {time.time() - overall_start:.4f}s")
        
        referendum_data = {}
        tasks = []
        
        # Create tasks for each network
        for network_id, opengov in self.network_opengov.items():
            substrate_api = self.network_apis.get(network_id)
            if not substrate_api:
                self.logger.error(f"No SubstrateAPI instance found for network {network_id}")
                continue
                
            # Get network config and extract network_name
            network_config = await self.network_manager.get_network(network_id)
            if not network_config:
                self.logger.error(f"Could not get network config for {network_id}")
                continue
                
            network_name = network_config.get('network_name', network_id)
                
            # Create a task for this network
            task = asyncio.create_task(self._check_network_referendums(network_id, network_name, opengov, substrate_api))
            tasks.append(task)
            
        # Wait for all tasks to complete
        print(f"DEBUG: Waiting for {len(tasks)} network tasks at {time.time() - overall_start:.4f}s")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print(f"DEBUG: All network tasks completed at {time.time() - overall_start:.4f}s")
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error checking referendums for network {i}: {result}")
                continue
                
            network_id, data = result
            referendum_data[network_id] = data
            
        print(f"DEBUG: Total check_all_referendums time: {time.time() - overall_start:.4f}s")
        return referendum_data
        
    async def _check_network_referendums(self, network_id, network_name, opengov, substrate_api):
        """Check referendums for a single network."""
        import time
        start_time = time.time()
        print(f"DEBUG: Starting referendum check for {network_id} at {time.time() - start_time:.4f}s")
        
        try:
            # Call check_referendums with the required parameters
            result = await opengov.check_referendums(network_name, substrate_api)
            
            if result is None:
                self.logger.error(f"check_referendums returned None for {network_id}")
                print(f"DEBUG: Completed referendum check for {network_id} (None result) at {time.time() - start_time:.4f}s")
                return network_id, (False, None)
            else:
                # The check_referendums method only returns new_referendums, not a tuple
                # We need to get the referendum_info separately
                new_referendums = result
                
                # Get the full referendum info for this network
                try:
                    print(f"DEBUG: Starting referendumInfoFor for {network_id} at {time.time() - start_time:.4f}s")
                    if substrate_api:
                        referendum_info = await substrate_api.referendumInfoFor()
                    else:
                        referendum_info = {}
                        self.logger.error(f"No SubstrateAPI instance found for network {network_id}")
                    print(f"DEBUG: Completed referendumInfoFor for {network_id} at {time.time() - start_time:.4f}s")
                except Exception as e:
                    referendum_info = {}
                    self.logger.error(f"Error getting referendum info for {network_id}: {e}")
                
                print(f"DEBUG: Completed referendum check for {network_id} at {time.time() - start_time:.4f}s")
                return network_id, (new_referendums, referendum_info)
                
        except Exception as e:
            self.logger.error(f"Error checking referendums for {network_id}: {e}")
            print(f"DEBUG: Error in referendum check for {network_id} at {time.time() - start_time:.4f}s: {e}")
            return network_id, (False, None)

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
