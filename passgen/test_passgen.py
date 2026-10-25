import string
import unittest

from passgen import SETS, generate


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
        pwd = generate(length=32, lower=True, upper=True, digits=False, symbols=False)[0]
        self.assertTrue(set(pwd) <= set(string.ascii_letters))

    def test_empty_pools_rejected(self):
        with self.assertRaises(ValueError):
            generate(lower=False, upper=False, digits=False, symbols=False)

    def test_short_length_rejected(self):
        with self.assertRaises(ValueError):
            generate(length=2)

    def test_nonpositive_count_rejected(self):
        for count in (0, -1):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    generate(count=count)

    def test_nonpositive_length_rejected(self):
        with self.assertRaises(ValueError):
            generate(length=0)


class TestStrength(unittest.TestCase):
    def test_long_beats_short(self):
        from passgen import strength
        short = strength("abc123")
        long_ = strength("aB3!xY9#qW2!eR5$")
        self.assertGreater(long_["bits"], short["bits"])
        self.assertIn(long_["rating"], ("strong", "excellent"))

    def test_empty_is_zero(self):
        from passgen import strength
        self.assertEqual(strength(""), {"bits": 0.0, "rating": "weak"})

    def test_ambiguity_free_pool_has_lower_entropy(self):
        from passgen import strength
        ordinary = strength("abc123!")
        ambiguity_free = strength("abc123!", no_ambiguous=True)
        self.assertLess(ambiguity_free["bits"], ordinary["bits"])


if __name__ == "__main__":
    unittest.main()


class TestNoAmbiguous(unittest.TestCase):
    def test_lookalikes_removed(self):
        from passgen import AMBIGUOUS
        pwd = generate(length=48, no_ambiguous=True)[0]
        self.assertFalse(set(pwd) & AMBIGUOUS)

    def test_digits_pool_excludes_zero(self):
        for _ in range(20):
            pwd = generate(length=40, lower=False, upper=False, digits=True,
                           symbols=False, no_ambiguous=True)[0]
            self.assertNotIn("0", pwd)


class TestStrength(unittest.TestCase):
    def test_long_beats_short(self):
        from passgen import strength
        short = strength("abc123")
        long_ = strength("aB3!xY9#qW2!eR5$")
        self.assertGreater(long_["bits"], short["bits"])
        self.assertIn(long_["rating"], ("strong", "excellent"))

    def test_empty_is_zero(self):
        from passgen import strength
        self.assertEqual(strength(""), {"bits": 0.0, "rating": "weak"})


if __name__ == "__main__":
    unittest.main()


class TestPassphraseValidation(unittest.TestCase):
    def test_nonpositive_word_count_rejected(self):
        from passgen import passphrase
        for words in (0, -1):
            with self.subTest(words=words), self.assertRaises(ValueError):
                passphrase(words)

    def test_boolean_and_non_integer_word_counts_rejected(self):
        from passgen import passphrase
        for words in (True, 1.5, "3"):
            with self.subTest(words=words), self.assertRaises(ValueError):
                passphrase(words)

    def test_separator_must_be_string(self):
        from passgen import passphrase
        with self.assertRaises(ValueError):
            passphrase(3, separator=None)


class TestPassphrase(unittest.TestCase):
    def test_shape(self):
        from passgen import passphrase
        pp = passphrase(4)
        self.assertEqual(len(pp.split("-")), 4)
        self.assertTrue(all(w.isalpha() for w in pp.split("-")))

    def test_custom_separator(self):
        from passgen import passphrase
        self.assertIn(" ", passphrase(3, separator=" "))


if __name__ == "__main__":
    unittest.main()

class TestExcludeChars(unittest.TestCase):
    def test_excluded_chars_absent(self):
        pwd = generate(length=40, exclude_chars="aeiou")[0]
        self.assertFalse(set(pwd) & set("aeiou"))

    def test_full_exclusion_rejected(self):
        with self.assertRaises(ValueError):
            generate(length=16, lower=False, upper=False, digits=True,
                     symbols=False, exclude_chars="0123456789")


if __name__ == "__main__":
    unittest.main()

class TestMainSmoke(unittest.TestCase):
    def test_main_runs_with_flags(self):
        import subprocess
        import sys
        import os
        out = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "passgen.py"),
             "-l", "16", "-n", "1", "--no-ambiguous", "--exclude", "xyz"],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(out.stdout.strip()), 16)

    def test_passphrase_flag(self):
        import subprocess
        import sys
        import os
        out = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "passgen.py"),
             "--passphrase", "--words", "3"],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(out.stdout.strip().split("-")), 3)

    def test_passphrase_rejects_zero_words_and_count(self):
        import os
        import subprocess
        import sys
        script = os.path.join(os.path.dirname(__file__), "passgen.py")
        for args, message in (
            (["--passphrase", "--words", "0"], "words must be an integer of at least 1"),
            (["--passphrase", "--count", "0"], "--count must be at least 1"),
        ):
            with self.subTest(args=args):
                out = subprocess.run(
                    [sys.executable, script, *args], capture_output=True, text=True
                )
                self.assertEqual(out.returncode, 2)
                self.assertIn(message, out.stderr)


if __name__ == "__main__":
    unittest.main()


class TestGenerateArgumentTypes(unittest.TestCase):
    def test_length_must_be_positive_integer(self):
        for length in (True, 1.5, "16", 0, -1):
            with self.subTest(length=length), self.assertRaises(ValueError):
                generate(length=length)

    def test_count_must_be_positive_integer(self):
        for count in (True, 1.5, "2", 0, -1):
            with self.subTest(count=count), self.assertRaises(ValueError):
                generate(count=count)

    def test_exclusions_must_be_a_string(self):
        with self.assertRaises(ValueError):
            generate(exclude_chars=None)
