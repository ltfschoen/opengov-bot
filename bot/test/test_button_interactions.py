"""
Test suite for testing Discord button interactions with the OpenGov Bot.

This module tests button click interactions (AYE, NAY, RECUSE) for voting
functionality, verifying that the buttons properly register votes and update
vote counts in referenda threads.
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock

from bot.test.core.test_env_jam_dao import JamDaoDiscordTestEnvironment
from bot.governance_monitor import GovernanceMonitor
from bot.utils.button_handler import ButtonHandler
from bot.config import Config


class ButtonInteractionsTest(unittest.TestCase):
    """Test case for button interactions on Discord referenda threads."""

    async def setup_test_environment(self):
        """Set up the test environment with a complete JAM DAO structure."""
        # Create test environment
        self.env = JamDaoDiscordTestEnvironment()
        await self.env.setup_jam_dao_structure()

        # Set up mock config
        config = MagicMock()
        config.DISCORD_ROLE = "dao-team-representative"
        config.ANONYMOUS_MODE = False
        config.NETWORK_NAME = "polkadot"

        # Create mock file paths for vote counts
        config.VOTE_COUNTS_FILE = ":memory:"  # In-memory storage for tests

        # Set up the governance monitor with our mocks
        self.env.bot.governance = GovernanceMonitor(self.env.bot, config)
        self.env.bot.governance.vote_counts = {}
        self.env.bot.governance.button_cooldowns = {}
        self.env.bot.governance.discord_role = "dao-team-representative"

        # Mock save/load vote counts methods (in-memory for tests)
        self.env.bot.governance.save_vote_counts = MagicMock(return_value=asyncio.Future())
        self.env.bot.governance.save_vote_counts.return_value.set_result(None)

        self.env.bot.governance.load_vote_counts = MagicMock(return_value=asyncio.Future())
        self.env.bot.governance.load_vote_counts.return_value.set_result({})

        # Mock fetch_channel
        async def mock_fetch_channel(channel_id):
            for channel_name, channel in self.env.channels.items():
                if hasattr(channel, "id") and channel.id == channel_id:
                    return channel
            return None

        self.env.bot.governance.fetch_channel = mock_fetch_channel
        self.env.bot.governance.user = self.env.users["bot_user"]

        # Create a referendum thread for testing
        self.referendum = await self.env.create_referendum_post(
            title="Test Referendum",
            content="This is a test referendum",
            author_name="dao_rep1",
            tags=["SmallSpender"]
        )

        # Add a vote results message at the beginning of the thread
        self.results_message = await self.referendum.send(
            content="👍 AYE: 0    |    👎 NAY: 0    |    ☯ RECUSE: 0",
            author=self.env.users["bot_user"]
        )

    async def test_button_voting(self):
        """Test voting with AYE, NAY, and RECUSE buttons."""
        await self.setup_test_environment()

        # Representatives who will vote
        reps = ["dao_rep1", "dao_rep2", "dao_rep3", "dao_rep4"]

        # Create a map of votes
        vote_map = {
            "dao_rep1": "aye_button",
            "dao_rep2": "aye_button",
            "dao_rep3": "nay_button",
            "dao_rep4": "recuse_button"
        }

        # Simulate button clicks for each rep
        for rep, vote in vote_map.items():
            result = await self.env.simulate_button_interaction(
                message_id=self.results_message.id,
                custom_id=vote,
                user_name=rep
            )

            self.assertTrue(result["success"], f"Button interaction failed for {rep}")
            self.assertEqual(result["user"], rep)
            self.assertEqual(result["vote_type"], vote.replace("_button", ""))

        # Check final vote counts
        message_id = str(self.results_message.id)
        vote_counts = self.env.bot.governance.vote_counts.get(message_id, {})

        self.assertEqual(vote_counts.get("aye", 0), 2, "Expected 2 AYE votes")
        self.assertEqual(vote_counts.get("nay", 0), 1, "Expected 1 NAY vote")
        self.assertEqual(vote_counts.get("recuse", 0), 1, "Expected 1 RECUSE vote")

        # Check that user votes are recorded correctly
        users = vote_counts.get("users", {})
        for rep, vote in vote_map.items():
            vote_type = vote.replace("_button", "")
            user_id = str(self.env.users[rep].id)
            self.assertIn(user_id, users)
            self.assertEqual(users[user_id]["vote_type"], vote_type)

    async def test_vote_change(self):
        """Test changing votes from one option to another."""
        await self.setup_test_environment()

        # First vote AYE
        result = await self.env.simulate_button_interaction(
            message_id=self.results_message.id,
            custom_id="aye_button",
            user_name="dao_rep1"
        )
        self.assertTrue(result["success"])

        # Check vote count
        message_id = str(self.results_message.id)
        vote_counts = self.env.bot.governance.vote_counts.get(message_id, {})
        self.assertEqual(vote_counts.get("aye", 0), 1)

        # Change vote to NAY
        result = await self.env.simulate_button_interaction(
            message_id=self.results_message.id,
            custom_id="nay_button",
            user_name="dao_rep1"
        )
        self.assertTrue(result["success"])

        # Check vote counts reflect the change
        vote_counts = self.env.bot.governance.vote_counts.get(message_id, {})
        self.assertEqual(vote_counts.get("aye", 0), 0, "AYE vote should be removed")
        self.assertEqual(vote_counts.get("nay", 0), 1, "NAY vote should be added")

        # Verify user's vote was updated
        user_id = str(self.env.users["dao_rep1"].id)
        self.assertEqual(vote_counts["users"][user_id]["vote_type"], "nay")

    async def test_non_representative_vote(self):
        """Test that non-representatives cannot vote."""
        await self.setup_test_environment()

        # Try voting with a participant user (should fail)
        result = await self.env.simulate_button_interaction(
            message_id=self.results_message.id,
            custom_id="aye_button",
            user_name="participant1"
        )

        self.assertFalse(result["success"])

        # Verify no votes were recorded
        message_id = str(self.results_message.id)
        vote_counts = self.env.bot.governance.vote_counts.get(message_id, {})
        if vote_counts:
            self.assertEqual(vote_counts.get("aye", 0), 0, "Non-representative should not be able to vote")


# Run tests if this module is executed directly
if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()
    test_suite.addTest(ButtonInteractionsTest())

    # Run the test suite asynchronously
    loop = asyncio.get_event_loop()

    # Create and run the tests
    async def run_tests():
        test_button = ButtonInteractionsTest()
        await test_button.test_button_voting()
        await test_button.test_vote_change()
        await test_button.test_non_representative_vote()

    loop.run_until_complete(run_tests())
    print("All button interaction tests completed")
