#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC Music Suite - ABC記法楽譜バリデーター

AIが生成した楽譜テキスト（ABC記法）の構文、使用文字、および拍数をチェックし、
エラーを検出して差し戻しを支援するためのフィルタリング処理を提供します。
"""

import re

def check_format(abc: str) -> tuple[bool, str]:
    """① ABC形式チェックフィルタ (M:, L:, K: が含まれているか)"""
    required = ["M:", "L:", "K:"]
    for r in required:
        if r not in abc:
            return False, f"{r} がありません"
    return True, "OK"


def check_character(abc: str) -> tuple[bool, str]:
    """② 使用文字チェックフィルタ 訂正版"""
    pattern = (
        r'^[A-Za-z0-9'
        r'\|\[\]:,_\'"/=\^\-\+\s\n'
        r'<>!().%]*$'
    )
    if re.fullmatch(pattern, abc):
        return True, "OK"
    return False, "ABC記法で使用できない文字があります"


def note_length(token: str) -> float:
    """
    ABC記法の音価を拍数（L:1/4 基準）で返す。
    """
    # 音価が指定されているか（例: C2, C3/2, C/2, C/）
    m = re.search(r'(\d+(/\d+)?|/\d*)$', token)
    if m is None:
        return 1.0

    value = m.group()

    if value == "/":
        # / 単体は半拍 (0.5拍) として処理
        return 0.5

    if value.startswith("/"):
        # /2 → 0.5拍
        try:
            return 1 / int(value[1:])
        except ValueError:
            return 1.0

    elif "/" in value:
        # 3/2 → 1.5拍
        try:
            num, den = value.split("/")
            return int(num) / int(den)
        except ValueError:
            return 1.0
    else:
        # 2, 4
        try:
            return float(value)
        except ValueError:
            return 1.0


def get_l_factor(abc: str) -> float:
    """
    L:1/8 などのヘッダーから音価補正係数を取得する。
    デフォルトは L:1/4 (factor=1.0) とし、L:1/8 なら factor=0.5 とする。
    """
    for line in abc.splitlines():
        if line.startswith("L:"):
            val = line[2:].strip()
            if "/" in val:
                try:
                    num, den = val.split("/")
                    # L:1/4を1.0拍基準とすると、L:1/8は 4/8 = 0.5拍
                    return 4 / int(den)
                except Exception:
                    pass
    return 1.0  # デフォルトは 1/4 とする


def get_meter_beats(abc: str) -> float:
    """
    M:4/4 などのヘッダーから1小節あたりの基準拍数（L:1/4基準）を取得する。
    デフォルトは 4.0 拍とする。
    """
    for line in abc.splitlines():
        if line.strip().startswith("M:"):
            val = line.split(":", 1)[1].strip()
            if val == "C":
                return 4.0
            if val == "C|":
                return 2.0
            if "/" in val:
                try:
                    num, den = val.split("/")
                    return (int(num) / int(den)) * 4.0
                except Exception:
                    pass
    return 4.0


def check_measure(abc: str) -> tuple[bool, str]:
    """③ 拍子チェックフィルタ (小節ごとの合計拍数が設定された拍子になっているか)"""
    music = []
    for line in abc.splitlines():
        # 行頭が英文字1文字＋コロンで始まる場合はヘッダー行（または歌詞行など）とみなして除外
        if re.match(r'^[A-Za-z]:', line.strip()):
            continue
        music.append(line)

    music = "".join(music)
    bars = music.split("|")

    # 音符にマッチする正規表現 (休符 z も含む)
    pattern = re.compile(
        r'[\^_=]*[A-Ga-gzZ][,\']*(\d+(/\d+)?|/\d*)?'
    )

    factor = get_l_factor(abc)
    target_beats = get_meter_beats(abc)
    measure_index = 0

    for bar in bars:
        # 小節の両端の空白や、反復記号などの装飾文字を除外
        bar_clean = bar.replace(":", "").replace("[", "").replace("]", "").strip()
        # 小節線のみや空の小節、終止線などはスキップ
        if not bar_clean or bar_clean in ["]", "[", "::", "||", "|"]:
            continue

        measure_index += 1
        total = 0.0
        for token in pattern.finditer(bar_clean):
            total += note_length(token.group()) * factor

        # 最初の小節（弱起 - upbeat）は、拍数が1小節分以下であれば許容する
        if measure_index == 1:
            if total > target_beats + 0.001:
                return False, f"1小節目（弱起）の拍数({total}拍)が指定拍子({target_beats}拍)を超えています"
        else:
            if abs(total - target_beats) > 0.001:
                return False, f"{measure_index}小節目が{total}拍です (指定拍子: {target_beats}拍)"

    return True, "OK"


def check_all(abc: str) -> tuple[bool, str]:
    """④ 全体チェック"""
    checks = [
        check_format,
        check_character,
        check_measure
    ]

    for check in checks:
        ok, message = check(abc)
        if not ok:
            return False, message

    return True, "すべてOK"
