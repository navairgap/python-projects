import string
import unittest

from passgen import generate


class ExclusionPoolCountTests(unittest.TestCase):
    def test_length_is_checked_after_empty_pools_are_removed(self):
        password = generate(
            length=1,
            lower=True,
            upper=True,
            digits=True,
            symbols=True,
            exclude_chars=string.ascii_lowercase + string.ascii_uppercase + string.digits,
        )[0]
        self.assertEqual(len(password), 1)
        self.assertIn(password, "!@#$%^&*()-_=+[]{};:,.<>?")

    def test_still_rejects_length_below_remaining_required_pools(self):
        with self.assertRaisesRegex(ValueError, "too short"):
            generate(
                length=1,
                lower=True,
                upper=True,
                digits=True,
                symbols=False,
                exclude_chars="abcdefghijklmnopqrstuvwxyz",
            )


if __name__ == "__main__":
    unittest.main()
