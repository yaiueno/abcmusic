# test_validator.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import abc_validator

# 1. 正しいABC (L:1/8 基準で E2 G2 c2 d2 は 2/8*4 = 8/8 = 1.0音符*4 = 4拍)
abc_ok = """X:1
T:Test
M:4/4
L:1/8
Q:120
K:C
|: E2 G2 c2 d2 | e3 d c4 | d2 B2 G3 A | B2 A2 G4 :|"""

print("Test 1 (OK):", abc_validator.check_all(abc_ok))

# 2. 形式エラー (M: がない)
abc_err_format = """X:1
T:Test
L:1/8
Q:120
K:C
|: E2 G2 c2 d2 | e3 d c4 :|"""

print("Test 2 (Format Error):", abc_validator.check_all(abc_err_format))

# 3. 文字エラー (全角文字など)
abc_err_char = """X:1
T:Test
M:4/4
L:1/8
Q:120
K:C
|: E2 G2 c2 d2 # | e3 d c4 :|"""  # # は許可文字に含まれていません

print("Test 3 (Char Error):", abc_validator.check_all(abc_err_char))

# test_validator.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import abc_validator

# 4. 拍数エラー (L:1/8基準で 1小節目が E3 G2 c2 d2 = 3/8 + 2/8 + 2/8 + 2/8 = 9/8音符 = 4.5拍)
abc_err_measure = """X:1
T:Test
M:4/4
L:1/8
Q:120
K:C
|: E3 G2 c2 d2 | e3 d c4 :|"""

print("Debug checking for Test 4:")
music = []
for line in abc_err_measure.splitlines():
    if ":" not in line or line.startswith("w:"):
        music.append(line)
music = "".join(music)
print("Extracted music content:", repr(music))
bars = music.split("|")
factor = abc_validator.get_l_factor(abc_err_measure)
print("Factor:", factor)

for i, bar in enumerate(bars):
    bar_clean = bar.replace(":", "").replace("[", "").replace("]", "").strip()
    if not bar_clean or bar_clean in ["]", "[", "::", "||", "|"]:
        continue
    total = 0.0
    tokens = []
    import re
    pattern = re.compile(r'[\^_=]*[A-Ga-gzZ][,\']*(\d+(/\d+)?|/\d*)?')
    for token in pattern.finditer(bar_clean):
        val = token.group()
        length = abc_validator.note_length(val)
        total += length * factor
        tokens.append((val, length))
    print(f"Bar {i+1} clean: {repr(bar_clean)}, Tokens: {tokens}, Total beats: {total}")

print("Test 4 (Measure Error Result):", abc_validator.check_all(abc_err_measure))


# 5. 3/4拍子のワルツ (M:3/4, 各小節 3拍)
abc_waltz = """X:1
T:Waltz Test
M:3/4
L:1/4
Q:140
K:G
|: G2 B | d2 g | f2 a | g3 :|"""

print("Test 5 (3/4 Waltz OK):", abc_validator.check_all(abc_waltz))


# 6. 弱起 (1小節目が 2拍、残りは 4拍)
abc_upbeat = """X:1
T:Upbeat Test
M:4/4
L:1/4
Q:120
K:C
E2 | C D E F | G3 A | G2 E2 | C4 |"""

print("Test 6 (Upbeat/Pickup Measure OK):", abc_validator.check_all(abc_upbeat))


