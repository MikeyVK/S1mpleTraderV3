
import json

def test_json(name, raw_str):
    print(f"Testing {name}: {raw_str}")
    try:
        data = json.loads(raw_str)
        print(f"  -> SUCCESS: {data}")
    except Exception as e:
        print(f"  -> FAILED: {type(e).__name__}: {e}")

# \uD83D\uDE80 is Rocket Emoji ðŸš€
# VS Code might send split surrogates like "\\uD83D\\uDE80" literally in the text
pair = r'{"key": "\uD83D\uDE80"}' 
test_json("Correct Pair", pair)

# Broken/Split surrogates often appear as separate escaped sequences 
# that don't combine automatically in some parsers
split = r'{"key": "\uD83D\uDE80"}' 
test_json("Split Pair", split)

# Lone surrogate
lone = r'{"key": "\uD83D"}'
test_json("Lone Surrogate", lone)
