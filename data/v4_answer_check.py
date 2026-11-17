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


CUR = re.compile(r"[$€£¥₹₩₽¢]|(?<![a-z])(?:usd|eur|gbp|inr|aed|rs|c\$|a\$)(?![a-z])")  # "inr8,109" counts as INR


# tokens that change an answer's meaning when dropped (Codex data audit #4: "12M"->"12", "Oct 4"->"4", "9:30 PM"->"9:30")
ESSENTIAL = {"k", "m", "b", "bn", "mn", "thousand", "million", "billion", "trillion", "lakh", "lakhs", "crore", "crores",
             "am", "pm", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
             "january", "february", "march", "april", "june", "july", "august", "september", "october", "november",
             "december", "mon", "tue", "wed", "thu", "fri", "sat", "sun", "monday", "tuesday", "wednesday", "thursday",
             "friday", "saturday", "sunday", "today", "tomorrow", "yesterday", "hr", "hrs", "hour", "hours", "min",
             "mins", "minute", "minutes", "sec", "secs", "second", "seconds", "day", "days", "week", "weeks", "month",
             "months", "year", "years", "km", "mi", "kg", "lb", "lbs", "gb", "mb", "tb", "kb"}


def essential(s):
    s = re.sub(r"(\d)\s*([ap])\.?(?:m\.?)?(?![a-z])", lambda m: m.group(1) + " " + m.group(2) + "m", s)  # 5:00p -> 5:00 pm
    t = set(re.findall(r"[a-z]+", re.sub(r"(\d)([a-z])", r"\1 \2", s)))  # "12m" -> "12 m"
    return (t & ESSENTIAL) | ({"%"} if "%" in s else set())


def same_answer(a, b):
    a, b = norm(a), norm(b)
    if a and b and essential(a) != essential(b):
        return False
    if not a or not b or "none" in (a, b):
        return False
    if sorted(CUR.findall(a)) != sorted(CUR.findall(b)) and CUR.findall(a) and CUR.findall(b):
        return False  # "$10" vs "€10"
    if (words(a) & NEG) != (words(b) & NEG):
        return False
    na, nb = nums(a), nums(b)
    if na or nb:
        if na != nb:
            return False
        short, long_ = sorted((a, b), key=len)
        return words(short) <= words(long_)
    return a == b


FILLER = {"the", "a", "an", "is", "are", "it", "its", "of", "about", "approximately", "approx", "around", "total"}


def gate_answer(pred, gold):
    """Development-gate scoring (Codex recovery audit P2): same_answer, and the prediction may not ADD content words to the
    reference ('12M is incorrect' vs '12M' fails; '12M downloads' vs '12M' fails too -- conservative)."""
    return same_answer(pred, gold) and (words(norm(pred)) - words(norm(gold))) <= FILLER


def exact_answer(pred, gold):
    """RL reward / strict scoring: equal after normalisation only (case, whitespace, quotes, trailing period, thousands
    separators, spacing around currency). No added or dropped words: '12M is incorrect' != '12M'."""
    f = lambda x: re.sub(r"(?<=\d),(?=\d{3}\b)", "", re.sub(r"([$€£¥₹₩₽¢])\s+", r"\1", norm(x)))
    return bool(norm(pred)) and f(pred) == f(gold)


def preferred(answer, verify):
    """The shorter of two agreeing answers when it only drops unit/filler words (e.g. '382 Followers' -> '382')."""
    a, v = str(answer or "").strip(), str(verify or "").strip()
    if v and len(v) < len(a) and same_answer(a, v) and nums(norm(a)) == nums(norm(v)) and nums(norm(a)):
        return v
    return a


def safe_short(long_answer, short):
    """ScreenQA shortening is accepted only if it keeps every number and negation of the original and is a substring."""
    L, S = norm(long_answer), norm(short)
    if not S or len(S) >= len(L) or not re.search(r"(?<![a-z0-9])" + re.escape(S) + r"(?![a-z0-9])", L):
        return False  # whole-token span only: "available" is not a span of "unavailable"
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
    for x, y in [("$10", "€10"), ("-5", "5"), ("100", "1000"), ("available", "unavailable")]:
        assert not same_answer(x, y), (x, y)
    assert not safe_short("It is unavailable.", "available") and not safe_short("10:49 PM on Jan 31, 2017", "10:49 PM on Jan 31 2017")
    assert not safe_short("1.50", "150")
    for x, y in [("12M", "12"), ("22K", "22"), ("Oct 4", "4"), ("9:30 PM", "9:30"), ("45%", "45"), ("4 GB", "4")]:
        assert not same_answer(x, y), (x, y)
    assert same_answer("12M", "12m") and same_answer("Oct 4", "oct 4") and same_answer("382 Followers", "382")
    assert not same_answer("INR8,109.08", "€8,109.08") and not same_answer("5:00p", "5:00") and same_answer("5:00 PM", "5:00pm")
    assert exact_answer("12M", "12m") and not exact_answer("12M is incorrect", "12M") and exact_answer("8,109.08", "8109.08")
    assert exact_answer("$ 10", "$10") and not exact_answer("$10", "€10") and not exact_answer("", "")
    print("answer-check tests pass")
