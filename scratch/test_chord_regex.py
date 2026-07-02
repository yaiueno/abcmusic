import re

def test():
    bar = '"C" [CEG]2 "Dm" [DFA]2'
    # Remove chord symbols
    bar_clean = re.sub(r'"[^"]*"', '', bar)
    print("Cleaned bar:", repr(bar_clean))
    
    # Match pattern
    pattern = re.compile(r'(?:\[[^\]]+\]|[\^_=]*[A-Ga-gzZ][,\']*)(\d+(/\d+)?|/\d*)?')
    matches = [m.group() for m in pattern.finditer(bar_clean)]
    print("Matches:", matches)

if __name__ == '__main__':
    test()
