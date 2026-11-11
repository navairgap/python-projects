import os
import string
import subprocess
import sys
import unittest

from passgen import AMBIGUOUS, SETS, generate, passphrase, strength

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "passgen.py")


def run_cli(arguments):
    command = [sys.executable, SCRIPT]
    command.extend(arguments)
    return subprocess.run(command, capture_output=True, text=True, check=False)


class TestGenerate(unittest.TestCase):
    def test_length_and_count(self):
        pwds = generate(length=24, count=5)
        self.assertEqual(len(pwds), 5)
        self.assertTrue(all(len(p) == 24 for p in pwds))

    def test_guarantees_each_set(self):
        for _ in range(50):  # shuffle is random — sample generously
            pwd = generate(length=8)[0]
            for pool in SETS.values():
                self.assertTrue(set(pwd) & set(pool), f"missing {pool!r} in {pwd}")

    def test_subset_selection(self):
        pwd = generate(length=32, digits=False, symbols=False)[0]
        self.assertTrue(set(pwd) <= set(string.ascii_letters))

    def test_empty_pools_rejected(self):
        with self.assertRaises(ValueError):
            generate(lower=False, upper=False, digits=False, symbols=False)

    def test_short_length_rejected(self):
        with self.assertRaises(ValueError):
            generate(length=2)

    def test_nonpositive_length_rejected(self):
        with self.assertRaises(ValueError):
            generate(length=0)

    def test_nonpositive_count_rejected(self):
        for count in (0, -1):
            with self.subTest(count=count), self.assertRaises(ValueError):
                generate(count=count)

    def test_length_must_be_positive_integer(self):
        for length in (True, 1.5, "16"):
            with self.subTest(length=length), self.assertRaises(ValueError):
                generate(length=length)

    def test_count_must_be_positive_integer(self):
        for count in (True, 1.5, "2"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                generate(count=count)


class TestExclusions(unittest.TestCase):
    def test_lookalikes_removed(self):
        pwd = generate(length=48, no_ambiguous=True)[0]
        self.assertFalse(set(pwd) & AMBIGUOUS)

    def test_digits_pool_excludes_zero(self):
        for _ in range(20):
            pwd = generate(length=40, lower=False, upper=False, digits=True,
                           symbols=False, no_ambiguous=True)[0]
            self.assertNotIn("0", pwd)

    def test_excluded_chars_absent(self):
        pwd = generate(length=40, exclude_chars="aeiou")[0]
        self.assertFalse(set(pwd) & set("aeiou"))

    def test_exclusions_must_be_a_string(self):
        with self.assertRaises(ValueError):
            generate(exclude_chars=None)

    def test_full_exclusion_rejected(self):
        with self.assertRaises(ValueError):
            generate(length=16, lower=False, upper=False, digits=True,
                     symbols=False, exclude_chars="0123456789")

    def test_length_is_checked_after_empty_pools_are_removed(self):
        password = generate(
            length=1,
            exclude_chars=string.ascii_letters + string.digits,
        )[0]
        self.assertEqual(len(password), 1)
        self.assertIn(password, "!@#$%^&*()-_=+[]{};:,.<>?")

    def test_still_rejects_length_below_remaining_required_pools(self):
        with self.assertRaisesRegex(ValueError, "too short"):
            generate(length=1, symbols=False, exclude_chars=string.ascii_lowercase)


class TestStrength(unittest.TestCase):
    def test_long_beats_short(self):
        short = strength("abc123")
        long_ = strength("aB3!xY9#qW2!eR5$")
        self.assertGreater(long_["bits"], short["bits"])
        self.assertIn(long_["rating"], ("strong", "excellent"))

    def test_empty_is_zero(self):
        self.assertEqual(strength(""), {"bits": 0.0, "rating": "weak"})

    def test_ambiguity_free_pool_has_lower_entropy(self):
        ordinary = strength("abc123!")
        ambiguity_free = strength("abc123!", no_ambiguous=True)
        self.assertLess(ambiguity_free["bits"], ordinary["bits"])

    def test_rejects_non_string_passwords(self):
        for password in (None, 7, [], {}):
            with self.subTest(password=password), self.assertRaises(ValueError):
                strength(password)

    def test_requires_boolean_ambiguity_flag(self):
        with self.assertRaises(ValueError):
            strength("example-password", no_ambiguous=1)

    def test_accounts_for_excluded_characters(self):
        ordinary = strength("aaaa")
        restricted = strength("aaaa", exclude_chars="bcdefghijklmnopqrstuvwxyz")
        self.assertGreater(ordinary["bits"], restricted["bits"])
        self.assertEqual(restricted["bits"], 0.0)

    def test_requires_string_exclusions(self):
        with self.assertRaises(ValueError):
            strength("example-password", exclude_chars=None)


class TestPassphrase(unittest.TestCase):
    def test_shape(self):
        pp = passphrase(4)
        self.assertEqual(len(pp.split("-")), 4)
        self.assertTrue(all(w.isalpha() for w in pp.split("-")))

    def test_custom_separator(self):
        self.assertIn(" ", passphrase(3, separator=" "))

    def test_nonpositive_word_count_rejected(self):
        for words in (0, -1):
            with self.subTest(words=words), self.assertRaises(ValueError):
                passphrase(words)

    def test_boolean_and_non_integer_word_counts_rejected(self):
        for words in (True, 1.5, "3"):
            with self.subTest(words=words), self.assertRaises(ValueError):
                passphrase(words)

    def test_separator_must_be_string(self):
        with self.assertRaises(ValueError):
            passphrase(3, separator=None)


class TestMainSmoke(unittest.TestCase):
    """End-to-end runs of passgen.py as a subprocess."""

    def test_main_runs_with_flags(self):
        out = run_cli(["-l", "16", "-n", "1", "--no-ambiguous", "--exclude", "xyz"])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(out.stdout.strip()), 16)

    def test_passphrase_flag(self):
        out = run_cli(["--passphrase", "--words", "3"])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(out.stdout.strip().split("-")), 3)

    def test_passphrase_rejects_zero_words_and_count(self):
        for arguments, message in (
            (["--passphrase", "--words", "0"], "words must be an integer of at least 1"),
            (["--passphrase", "--count", "0"], "--count must be at least 1"),
        ):
            with self.subTest(arguments=arguments):
                out = run_cli(arguments)
                self.assertEqual(out.returncode, 2)
                self.assertIn(message, out.stderr)


if __name__ == "__main__":
    unittest.main()
