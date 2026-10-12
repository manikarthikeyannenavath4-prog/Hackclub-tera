import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import game


class TestGuessingGame(unittest.TestCase):
    def test_invalid_then_valid_guess_still_works(self):
        with patch("builtins.input", side_effect=["abc", "50"]), patch("random.randint", return_value=50):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                game.play_game()
            output = buffer.getvalue()

        self.assertIn("invalid input", output.lower())
        self.assertIn("Congratulations! You guessed the number", output)

    def test_low_guess_reports_too_low(self):
        with patch("builtins.input", side_effect=["10"]), patch("random.randint", return_value=50):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                game.play_game()
            output = buffer.getvalue()

        self.assertIn("Too Low!", output)


if __name__ == "__main__":
    unittest.main()
