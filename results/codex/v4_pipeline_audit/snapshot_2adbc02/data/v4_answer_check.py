"""Strict, type-aware answer comparison for v4 teacher labels (replaces the permissive agree() used at generation time).

Codex research (results/codex/codex_overnight_research.md) found false agreements in the generation-time check:
1.5/15, -2/2, 1:30/130, York/New York, "no alerts"/alerts. Rules here:
  * normalise: lower-case, collapse whitespace, strip surrounding quotes and a trailing period;
  * numeric answers: the ordered list of number tokens (sign, decimals, thousands separators, times like 1:30 kept
    intact) must be identical; remaining words of the shorter answer must be a whole-word subset of the longer one
    ("382 followers" ~ "382", but "1.5" != "15", "-2" != "2", "1:30" != "130");
  * non-numeric answers: exact equality after normalisation (no substring matches: "york" != "new york");
  * negation guard: if either side contains a negation word the other lacks, reject.
"""
import re

NUM = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?(?::\d+)*")
NEG = {"no", "not", "none", "never", "nothing", "without", "zero", "isn't", "aren't", "doesn't", "don't", "can't", "cannot"}


def norm(s):
    s = re.sub(r"\s+", " ", str(s or "").strip().lower())
    s = s.strip("\"'`“”‘’ ")
    return s[:-1] if s.endswith(".") and not re.search(r"\d\.$", s) else s


def nums(s):
    return [n.replace(",", "") for n in NUM.findall(s)]


def words(s):
    return set(re.findall(r"[a-z]+(?:'[a-z]+)?", NUM.sub(" ", s)))


def same_answer(a, b):
    a, b = norm(a), norm(b)
    if not a or not b or "none" in (a, b):
        return False
    if (words(a) & NEG) != (words(b) & NEG):
        return False
    na, nb = nums(a), nums(b)
    if na or nb:
        if na != nb:
            return False
        short, long_ = sorted((a, b), key=len)
        return words(short) <= words(long_)
    return a == b


def preferred(answer, verify):
    """The shorter of two agreeing answers when it only drops unit/filler words (e.g. '382 Followers' -> '382')."""
    a, v = str(answer or "").strip(), str(verify or "").strip()
    if v and len(v) < len(a) and same_answer(a, v) and nums(norm(a)) == nums(norm(v)) and nums(norm(a)):
        return v
    return a


def safe_short(long_answer, short):
    """ScreenQA shortening is accepted only if it keeps every number and negation of the original and is a substring."""
    L, S = norm(long_answer), norm(short)
    if not S or S not in L or len(S) >= len(L):
        return False
    if (words(L) & NEG) - (words(S) & NEG):
        return False
    return all(n in nums(S) for n in nums(L))


if __name__ == "__main__":
    bad = [("1.5", "15"), ("-2", "2"), ("1:30", "130"), ("York", "New York"), ("no alerts", "alerts")]
    good = [("382 Followers", "382"), ("C$43.00", "C$43.00"), ("6:16 AM", "6:16 am"), ("4.2", "4.2."), ("Sun", "sun"),
            ("410,000+ results", "410,000+"), ("₹614", "₹614")]
    for x, y in bad:
        assert not same_answer(x, y), (x, y)
    for x, y in good:
        assert same_answer(x, y), (x, y)
    assert preferred("382 Followers", "382") == "382" and preferred("York", "New York") == "York"
    assert safe_short("The temperature today is 51°.", "51°") and not safe_short("There are no alerts", "alerts")
    assert not safe_short("3 of 5 stars", "3") and safe_short("Wednesday, Feb 1st, 2017", "Feb 1st, 2017")
    print("answer-check tests pass")
