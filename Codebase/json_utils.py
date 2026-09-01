"""Pull a JSON object out of an LLM response, repairing common local-LLM mistakes."""

import json
import re


def extract_json(text):
    """Return the first JSON object in `text` as a dict, or None if unparseable."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    raw = match.group(0)
    for candidate in (raw, _drop_trailing_commas(raw)):
        for variant in (candidate, _quote_before_bracket(candidate)):
            try:
                return json.loads(variant, strict=False)
            except json.JSONDecodeError:
                continue
    return None


def _drop_trailing_commas(text):
    return re.sub(r",\s*([}\]])", r"\1", text)


def _quote_before_bracket(text):
    """Local LLMs sometimes drop the closing quote on the last string before ']'
    (e.g. '...days.]}' instead of '...days."]}'). Insert it back."""
    out = []
    for c in text:
        if c == "]":
            j = len(out) - 1
            while j >= 0 and out[j] in " \t\n\r":
                j -= 1
            if (out[j] if j >= 0 else "") not in ('"', "}", "]", "["):
                out.append('"')
        out.append(c)
    return "".join(out)


def invoke_json(chain, inputs, attempts=3):
    """Invoke an LLM chain and parse its JSON output, retrying on failure -
    local LLMs occasionally return malformed JSON, and a retry usually fixes it."""
    for _ in range(attempts):
        data = extract_json(chain.invoke(inputs))
        if data is not None:
            return data
    return None


def merge_unique(primary, secondary, exclude=()):
    """Combine two lists, keeping primary's items and order first, then
    appending anything from secondary not already present (case-insensitive)
    or in exclude. Used to guarantee a generator's output doesn't silently
    drop items (e.g. skills) the model chose not to echo back."""
    excluded = {e.lower() for e in exclude}
    seen = {p.lower() for p in primary}
    merged = list(primary)
    for item in secondary:
        low = item.lower()
        if low not in seen and low not in excluded:
            merged.append(item)
            seen.add(low)
    return merged


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
