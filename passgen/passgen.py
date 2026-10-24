#!/usr/bin/env python3
"""passgen - a small password generator. stdlib only."""

import argparse
import secrets
import string

SETS = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "symbols": "!@#$%^&*()-_=+[]{};:,.<>?",
}


AMBIGUOUS = set("l1IO0")


def generate(length=16, lower=True, upper=True, digits=True, symbols=True, count=1,
             no_ambiguous=False, exclude_chars=""):
    if length < 1:
        raise ValueError("length must be at least 1")
    if count < 1:
        raise ValueError("count must be at least 1")
    pools = [chars for chars, on in (
        (SETS["lower"], lower), (SETS["upper"], upper),
        (SETS["digits"], digits), (SETS["symbols"], symbols),
    ) if on]
    if not pools:
        raise ValueError("at least one character set must be enabled")
    if length < len(pools):
        raise ValueError(f"length {length} too short for {len(pools)} character sets")

    alphabet = "".join(pools)
    for excl in (AMBIGUOUS if no_ambiguous else set()) | set(exclude_chars):
        pools = ["".join(c for c in pool if c != excl) for pool in pools]
    pools = [pool for pool in pools if pool]
    if not pools:
        raise ValueError("no characters left after exclusions")
    alphabet = "".join(pools)
    rng = secrets.SystemRandom()
    out = []
    for _ in range(count):
        chars = [secrets.choice(p) for p in pools]  # guarantee coverage
        chars += [secrets.choice(alphabet) for _ in range(length - len(pools))]
        rng.shuffle(chars)
        out.append("".join(chars))
    return out


def strength(password, no_ambiguous=False):
    """rough entropy estimate in bits + a word rating."""
    import math
    pools = 0
    for chars in (string.ascii_lowercase, string.ascii_uppercase,
                  string.digits, SETS["symbols"]):
        allowed = "".join(c for c in chars if not (no_ambiguous and c in AMBIGUOUS))
        if set(password) & set(allowed):
            pools += len(allowed)
    bits = len(password) * math.log2(pools) if pools else 0
    rating = "weak" if bits < 45 else "ok" if bits < 70 else "strong" if bits < 100 else "excellent"
    return {"bits": round(bits, 1), "rating": rating}


WORDS = ("amber binary cobalt delta ember frost glacier harbor ivory jasper "
         "krypton lunar meadow north orbit prism quartz riverstone solar timber "
         "umbra velvet willow xenon yellow zenith anchor beacon cipher drift "
         "engine fossil garnet hollow island jolt kernel lantern marble nova "
         "onyx pulse quiver relay summit turbine umber vortex window yield zephyr").split()


def passphrase(words=5, separator="-"):
    """Generate a passphrase containing a positive number of words."""
    if isinstance(words, bool) or not isinstance(words, int) or words < 1:
        raise ValueError("words must be an integer of at least 1")
    if not isinstance(separator, str):
        raise ValueError("separator must be a string")
    import secrets as _s
    return separator.join(_s.choice(WORDS) for _ in range(words))


def main():
    ap = argparse.ArgumentParser(description="generate passwords")
    ap.add_argument("-l", "--length", type=int, default=16)
    ap.add_argument("-n", "--count", type=int, default=1)
    ap.add_argument("--no-lower", action="store_true")
    ap.add_argument("--no-upper", action="store_true")
    ap.add_argument("--no-digits", action="store_true")
    ap.add_argument("--no-symbols", action="store_true")
    ap.add_argument("--no-ambiguous", action="store_true", help="drop lookalikes (l 1 I O 0)")
    ap.add_argument("--exclude", default="", help="characters to never use")
    ap.add_argument("-v", "--show-strength", action="store_true", help="print entropy rating")
    ap.add_argument("--passphrase", action="store_true", help="word-based passphrase instead")
    ap.add_argument("--words", type=int, default=5)
    a = ap.parse_args()

    if a.passphrase:
        if a.count < 1:
            ap.error("--count must be at least 1 for passphrases")
        try:
            for _ in range(a.count):
                print(passphrase(a.words))
        except ValueError as e:
            ap.error(str(e))
        return

    try:
        for pwd in generate(a.length, not a.no_lower, not a.no_upper,
                            not a.no_digits, not a.no_symbols, a.count,
                            a.no_ambiguous, a.exclude):
            if a.show_strength:
                s = strength(pwd, a.no_ambiguous)
                print(f"{pwd}   # {s['bits']} bits, {s['rating']}")
            else:
                print(pwd)
    except ValueError as e:
        ap.error(str(e))


if __name__ == "__main__":
    main()
