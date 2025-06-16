import json
import io
import unittest
from bot.utils.participation_rate import calculate_current_participation_rate


class ParticipationRateTest(unittest.TestCase):
    """Test cases for participation rate calculation functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.votes = {}
        self.members = {}

        # Load test fixtures
        try:
            with io.open("bot/test/fixtures/vote_counts.json", "r") as file:
                data = file.read()
                self.votes = json.loads(data)
        except FileNotFoundError:
            self.skipTest("Votes file not found")

        try:
            with io.open("bot/test/fixtures/members.json", "r") as file:
                data = file.read()
                self.members = json.loads(data)
        except FileNotFoundError:
            self.skipTest("Members file not found")

    def test_calculate_participation_rate(self):
        """Test participation rate calculation works correctly."""
        print("Running participation rate test")
        result = calculate_current_participation_rate(self.votes, self.members)

        # Verify result is a string containing participation rate data
        self.assertIsInstance(result, str)

        # Check result contains expected information
        self.assertIn("Participation Statistics:", result)
        self.assertIn("Total number of active proposals:", result)
        self.assertIn("Member Participation:", result)

        # Verify at least one member's participation data is included
        # Assumes at least one member is in test data
        if self.members:
            member_username = self.members[0]['username']
            self.assertIn(member_username, result)


if __name__ == "__main__":
    unittest.main()
