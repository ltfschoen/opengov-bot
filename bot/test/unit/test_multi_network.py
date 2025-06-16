import unittest
import asyncio
import json
import os
import sys
import tempfile
import shutil
import warnings
from unittest.mock import MagicMock, patch, AsyncMock

# Suppress RuntimeWarning about coroutines not being awaited
warnings.filterwarnings("ignore", message="coroutine '.*' was never awaited")
warnings.filterwarnings("ignore", message="Enable tracemalloc to get the object allocation traceback")

# Add the project root to sys.path to make imports work correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from utils directly when running tests
from bot.utils.network_manager import NetworkManager
from bot.utils.multi_network_handler import MultiNetworkHandler
from bot.utils.multi_network_governance import MultiNetworkGovernance


class TestMultiNetwork(unittest.TestCase):
    """Test suite for the multi-network functionality"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.networks_config_path = os.path.join(self.test_dir, "networks.json")

        # Create test network configuration
        test_config = {
            "polkadot": {
                "enabled": True,
                "network_name": "polkadot",
                "symbol": "DOT",
                "token_decimal": 10,
                "substrate_wss": "wss://rpc.polkadot.io",
                "people_wss": None,
                "forum_tags": []
            },
            "kusama": {
                "enabled": True,
                "network_name": "kusama",
                "symbol": "KSM",
                "token_decimal": 12,
                "substrate_wss": "wss://kusama-rpc.polkadot.io",
                "people_wss": None,
                "forum_tags": []
            }
        }

        with open(self.networks_config_path, 'w') as f:
            json.dump(test_config, f)

    def tearDown(self):
        """Clean up test environment after each test"""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    async def async_setup(self):
        """Async setup for network manager"""
        self.network_manager = NetworkManager(self.networks_config_path)
        await self.network_manager.load_networks()
        return self.network_manager

    def test_network_manager_initialization(self):
        """Test that NetworkManager correctly loads network configurations"""
        loop = asyncio.get_event_loop()
        network_manager = loop.run_until_complete(self.async_setup())

        # Check both networks are loaded
        networks = loop.run_until_complete(network_manager.get_all_networks())
        self.assertEqual(len(networks), 2)
        self.assertIn("polkadot", networks)
        self.assertIn("kusama", networks)

        # Check network properties
        polkadot = networks["polkadot"]
        self.assertEqual(polkadot["network_name"], "polkadot")
        self.assertEqual(polkadot["symbol"], "DOT")
        self.assertEqual(polkadot["token_decimal"], 10)

        kusama = networks["kusama"]
        self.assertEqual(kusama["network_name"], "kusama")
        self.assertEqual(kusama["symbol"], "KSM")
        self.assertEqual(kusama["token_decimal"], 12)

    @patch('bot.utils.multi_network_handler.SubstrateAPI')
    async def async_test_multi_network_handler(self, mock_substrate_api):
        """Test that MultiNetworkHandler correctly initializes connections"""
        # Configure mock
        mock_substrate_instance = AsyncMock()
        mock_substrate_api.return_value = mock_substrate_instance

        # Initialize network manager
        network_manager = NetworkManager(self.networks_config_path)
        await network_manager.load_networks()

        # Initialize handler
        handler = MultiNetworkHandler(network_manager)
        await handler.initialize_connections()

        # Verify connections were initialized for both networks
        self.assertEqual(len(handler.network_apis), 2)
        self.assertIn("polkadot", handler.network_apis)
        self.assertIn("kusama", handler.network_apis)

        # Test close connections
        await handler.close_connections()
        self.assertEqual(mock_substrate_instance.close.call_count, 2)

    def test_multi_network_handler(self):
        """Run the async test for MultiNetworkHandler"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_test_multi_network_handler())

    @patch('bot.utils.multi_network_governance.MultiNetworkHandler')
    @patch('bot.utils.multi_network_governance.NetworkManager')
    async def async_test_governance(self, mock_network_manager, mock_handler):
        """Test that MultiNetworkGovernance correctly fetches referenda"""
        # Configure mocks
        mock_network_manager_instance = AsyncMock()
        mock_network_manager.return_value = mock_network_manager_instance

        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance

        # Mock network_apis to be a regular dict instead of a coroutine
        mock_handler_instance.network_apis = {
            "polkadot": AsyncMock(),
            "kusama": AsyncMock()
        }

        # Make sure ongoing_referendums_idx returns a list, not a coroutine
        for api_mock in mock_handler_instance.network_apis.values():
            api_mock.ongoing_referendums_idx.return_value = ["123", "456"]
            # Configure close method to return a completed future to avoid warning
            api_mock.close.return_value = asyncio.Future()
            api_mock.close.return_value.set_result(None)

        # Mock check_all_referendums to return test data
        mock_handler_instance.check_all_referendums.return_value = {
            "polkadot": ({
                "123": {
                    "title": "Test Polkadot Referendum",
                    "content": "Test",
                    "successful_url": "https://polkadot.subsquare.io",
                    "onchain": {"origin": {"Council": True}}
                }
            }, {"123": {"status": "ongoing"}}),
            "kusama": ({
                "456": {
                    "title": "Test Kusama Referendum",
                    "content": "Test",
                    "successful_url": "https://kusama.subsquare.io",
                    "onchain": {"origin": {"Council": True}}
                }
            }, {"456": {"status": "ongoing"}})
        }

        # Create mock client with proper Discord mocks
        mock_client = AsyncMock()
        mock_client.config = MagicMock()
        mock_client.config.DISCORD_SERVER_ID = 12345

        # Mock Discord guild and channel
        mock_guild = AsyncMock()
        mock_client.get_guild.return_value = mock_guild

        # Configure mock_process to return a completed future
        mock_process = AsyncMock()
        mock_process.return_value = asyncio.Future()
        mock_process.return_value.set_result(None)

        # Configure mock_archive to return a completed future
        mock_archive = AsyncMock()
        mock_archive.return_value = asyncio.Future()
        mock_archive.return_value.set_result(None)

        # Patch methods with configured mocks
        with patch.object(MultiNetworkGovernance, '_process_network_referenda', mock_process):
            with patch.object(MultiNetworkGovernance, '_archive_inactive_proposals', mock_archive):
                # Initialize governance
                mock_discord_format = AsyncMock()
                governance = MultiNetworkGovernance(mock_client, mock_discord_format)

                # Start and check for governance
                await governance.start()
                await governance.check_governance()

                # Verify check_all_referendums was called
                mock_handler_instance.check_all_referendums.assert_called_once()

                # Verify patched methods were called
                mock_process.assert_called()
                mock_archive.assert_called()

    def test_governance(self):
        """Run the async test for MultiNetworkGovernance"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_test_governance())


if __name__ == '__main__':
    unittest.main()
