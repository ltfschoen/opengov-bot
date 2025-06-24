#!/usr/bin/env python3
import asyncio
import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot.utils.subquery import SubstrateAPI
from bot.utils.gov2 import OpenGovernance2
from bot.scripts.check_referenda import StandaloneConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug")

async def debug_referenda():
    config = StandaloneConfig()

    # Print configuration
    print(f"Network: {config.NETWORK_NAME}")
    print(f"WSS: {config.SUBSTRATE_WSS}")

    # Connect to substrate
    substrate = SubstrateAPI(config)
    await substrate.connect(config.SUBSTRATE_WSS)
    print("Connected to Substrate node successfully")

    # Initialize governance
    governance = OpenGovernance2(config, substrate)
    print("Initialized OpenGovernance2")

    # Get referendum info directly
    print("Fetching referendum info directly...")
    referendum_info = await substrate.referendumInfoFor()
    print(f"Found {len(referendum_info)} referendums")

    # Print details of each referendum
    for ref_id, ref_data in referendum_info.items():
        print(f"Referendum #{ref_id}:")
        print(f"  Data: {ref_data}")

        # Try to fetch more details
        try:
            ref_details = await governance.fetch_referendum_data(referendum_id=ref_id, network=config.NETWORK_NAME)
            print(f"  Title: {ref_details.get('title', 'No title')}")
            print(f"  Origin: {ref_details.get('origin', 'Unknown')}")
        except Exception as e:
            print(f"  Error fetching details: {e}")

    # Close connection
    await substrate.close()

if __name__ == "__main__":
    asyncio.run(debug_referenda())
