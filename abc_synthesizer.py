#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC記法の楽譜をパースし、WAV波形を合成して演奏するライブラリ
"""

import re
import math
import wave
import struct
import subprocess
import os
import sys

# 調号（Key Signature）ごとのデフォルトのシャープ/フラット設定
KEY_SIGNATURES = {
    'C': {}, 'Am': {},
    'G': {'F': '^'}, 'Em': {'F': '^'},
    'D': {'F': '^', 'C': '^'}, 'Bm': {'F': '^', 'C': '^'},
    'A': {'F': '^', 'C': '^', 'G': '^'}, 'F#m': {'F': '^', 'C': '^', 'G': '^'},
    'E': {'F': '^', 'C': '^', 'G': '^', 'D': '^'}, 'C#m': {'F': '^', 'C': '^', 'G': '^', 'D': '^'},
    'B': {'F': '^', 'C': '^', 'G': '^', 'D': '^', 'A': '^'},
    'F': {'B': '_'}, 'Dm': {'B': '_'},
    'Bb': {'B': '_', 'E': '_'}, 'Gm': {'B': '_', 'E': '_'},
    'Eb': {'B': '_', 'E': '_', 'A': '_'}, 'Cm': {'B': '_', 'E': '_', 'A': '_'},
    'Ab': {'B': '_', 'E': '_', 'A': '_', 'D': '_'},
}

# 音名からCからの半音ステップ数へのマッピング
# 大文字 C〜B はオクターブ4 (MIDI 60〜71)
# 小文字 c〜b はオクターブ5 (MIDI 72〜83)
NOTE_STEPS = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
    'c': 12, 'd': 14, 'e': 16, 'f': 17, 'g': 19, 'a': 21, 'b': 23
}

# 音符トークン抽出用正規表現
# 1. 和音: `[CEG]2` や `[C_E^G]` などのブラケット表現
# 2. 単音: `^C,2` などの臨時記号＋音名＋オクターブ＋長さ
TOKEN_PATTERN = re.compile(
    r'(?:\[([^\]]+)\]|([\^_]*=?)([A-Ga-gzxZ])([,\']*))(\d*/?\d*)'
)

# 和音内の単音解析用正規表現
CHORD_NOTE_PATTERN = re.compile(r'([\^_]*=?)([A-Ga-gzxZ])([,\']*)')


def parse_abc(abc_text):
    """
    ABC記法のテキストをヘッダー部と楽譜データ部に分解する
    """
    lines = abc_text.strip().split('\n')
    music_lines = []
    
    tempo = 120
    default_length = 0.125  # デフォルトは 1/8 音符
    key = 'C'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # コメント行を除外
        if line.startswith('%'):
            continue
            
        # ヘッダー情報の解析
        if len(line) > 2 and line[1] == ':' and line[0].isupper():
            header_type = line[0]
            val = line[2:].strip()
            
            if header_type == 'L':  # デフォルト音符の長さ (例: 1/8, 1/4)
                if '/' in val:
                    try:
                        num, den = val.split('/')
                        default_length = float(num) / float(den)
                    except ValueError:
                        pass
                else:
                    try:
                        default_length = float(val)
                    except ValueError:
                        pass
            elif header_type == 'Q':  # テンポ (例: 120, 1/4=120)
                # 最後の数字をテンポとして抽出
                match = re.search(r'(\d+)$', val)
                if match:
                    try:
                        tempo = int(match.group(1))
                    except ValueError:
                        pass
            elif header_type == 'K':  # 調 (例: C, G, Dm)
                # 調のメイン部分のみ取得 (空白で区切られた最初の単語)
                key = val.split()[0]
        else:
            # 楽譜データ行 (インラインコメント除去)
            clean_line = re.sub(r'%.*', '', line)
            music_lines.append(clean_line)
            
    music_content = ' '.join(music_lines)
    return music_content, default_length, tempo, key


def parse_duration(dur_str):
    """
    音符の長さを示す文字列を浮動小数の倍率に変換する (例: "2" -> 2.0, "/2" -> 0.5, "3/2" -> 1.5)
    """
    if not dur_str:
        return 1.0
    if dur_str == '/':
        return 0.5
    if '/' in dur_str:
        parts = dur_str.split('/')
        num = float(parts[0]) if parts[0] else 1.0
        den = float(parts[1]) if parts[1] else 2.0
        return num / den
    try:
        return float(dur_str)
    except ValueError:
        return 1.0


def get_note_frequency(accidental, note_name, octave_mod, key_sig):
    """
    音の要素（臨時記号、音名、オクターブ、調号）から周波数を計算する
    """
    if note_name.lower() in ('z', 'x'):
        return 0.0  # 休符
        
    # ベースの音階のステップ数を取得
    if note_name not in NOTE_STEPS:
        return 0.0
        
    step = NOTE_STEPS[note_name]
    midi_note = 60 + step  # C4を基準(60)とする
    
    # オクターブ修飾の適用
    for char in octave_mod:
        if char == ',':
            midi_note -= 12
        elif char == "'":
            midi_note += 12
            
    # 臨時記号または調号によるシャープ/フラットの適用
    if accidental:
        if '^' in accidental:
            midi_note += accidental.count('^')
        elif '_' in accidental:
            midi_note -= accidental.count('_')
        elif '=' in accidental:
            pass  # ナチュラル（調号を無視して元の音に戻す）
    else:
        # 調号による自動フラット/シャープの適用
        letter = note_name.upper()
        if letter in key_sig:
            sig_acc = key_sig[letter]
            if sig_acc == '^':
                midi_note += 1
            elif sig_acc == '_':
                midi_note -= 1
                
    # MIDI番号から周波数(Hz)を算出 (A4 = 69 = 440Hz)
    frequency = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
    return frequency


def generate_samples(music_content, default_length, tempo, key, sample_rate=22050):
    """
    楽譜情報からオーディオサンプル（波形データ）を合成する
    """
    # 基準音符1拍あたりの秒数 (Q:120, L:1/4 なら 1拍 0.5秒)
    default_note_seconds = (default_length / 0.25) * (60.0 / tempo)
    key_sig = KEY_SIGNATURES.get(key, {})
    
    samples = []
    
    # トークンを走査
    tokens = TOKEN_PATTERN.findall(music_content)
    
    for chord_notes, accidental, note_name, octave_mod, duration_str in tokens:
        duration_multiplier = parse_duration(duration_str)
        note_duration = duration_multiplier * default_note_seconds
        
        # 周波数のリストを生成（和音対応）
        frequencies = []
        if chord_notes:
            for m in CHORD_NOTE_PATTERN.finditer(chord_notes):
                acc, name, oct_mod = m.groups()
                freq = get_note_frequency(acc, name, oct_mod, key_sig)
                if freq > 0:
                    frequencies.append(freq)
        elif note_name:
            freq = get_note_frequency(accidental, note_name, octave_mod, key_sig)
            if freq > 0:
                frequencies.append(freq)
                
        num_samples = int(note_duration * sample_rate)
        
        # プチプチ音防止のためのフェード処理時間
        fade_in_samples = min(int(0.01 * sample_rate), int(num_samples * 0.1))
        fade_out_samples = min(int(0.04 * sample_rate), int(num_samples * 0.2))
        
        for i in range(num_samples):
            t = i / sample_rate
            
            if not frequencies:
                # 休符の場合
                val = 0.0
            else:
                # 倍音合成（温かみのあるフルート風シンセ音）
                val_sum = 0.0
                for freq in frequencies:
                    # 基音 (Sine)
                    val_sum += 0.5 * math.sin(2.0 * math.pi * freq * t)
                    # 第2倍音 (柔らかさ/オルガン風の厚みを追加)
                    val_sum += 0.25 * math.sin(4.0 * math.pi * freq * t)
                    # 第3倍音
                    val_sum += 0.1 * math.sin(6.0 * math.pi * freq * t)
                val = val_sum / len(frequencies)
                
            # エンベロープ（音の立ち上がりと消え方をなめらかにする）
            if i < fade_in_samples:
                envelope = i / fade_in_samples
            elif i > num_samples - fade_out_samples:
                envelope = (num_samples - i) / fade_out_samples
            else:
                envelope = 1.0
                
            samples.append(val * envelope)
            
    return samples


def save_wav(samples, filename, sample_rate=22050):
    """
    オーディオサンプルを16bit PCMモノラルのWAVファイルとして保存
    """
    # 正規化（クリッピング防止）
    max_val = max(abs(s) for s in samples) if samples else 0
    scale = 0.8 / max_val if max_val > 0.8 else 1.0
    
    with wave.open(filename, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        
        for s in samples:
            val = int(s * scale * 32767)
            val = max(-32768, min(32767, val)) # 範囲制限
            w.writeframesraw(struct.pack('<h', val))


def play_wav(filename):
    """
    プラットフォームに応じてWAVファイルを再生する
    """
    if not os.path.exists(filename):
        return
        
    if sys.platform.startswith('win'):
        try:
            import winsound
            winsound.PlaySound(filename, winsound.SND_FILENAME)
        except Exception as e:
            print("Windowsでの再生エラー:", e)
    else:
        # Linux (Raspberry Pi等)
        # aplay, paplay, play(SoX) の順で試行
        players = [
            ['aplay', '-q', filename],
            ['paplay', filename],
            ['play', '-q', filename]
        ]
        played = False
        for player in players:
            try:
                subprocess.run(player, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                played = True
                break
            except Exception:
                continue
        if not played:
            print("[警告] WAVファイルを再生するコマンド(aplay, paplay, play)が見つかりませんでした。")
            print("ラズパイ側で 'sudo apt-get install alsa-utils' 等を実行して再生コマンドをインストールしてください。")


def extract_abc_blocks(text):
    """
    テキスト中からABC記法の楽譜ブロックを抽出する
    """
    # 1. ```abc で囲まれたブロックを優先的に抽出
    blocks = re.findall(r'```abc\s*(.*?)\s*```', text, re.DOTALL)
    if blocks:
        return [b.strip() for b in blocks if b.strip()]
        
    # 2. マークダウン外で X: や K: が含まれているテキストブロックをフォールバック抽出
    if 'X:' in text and 'K:' in text:
        match = re.search(r'(X:\s*\d+.*?(?:K:[A-G][m#b]?.*?)(?:\n\n|\Z))', text, re.DOTALL)
        if match:
            return [match.group(1).strip()]
            
    return []


def play_abc_string(abc_text, output_wav="temp_abc.wav"):
    """
    ABC記法のテキストを直接パース・合成・再生する一連処理
    """
    music_content, default_length, tempo, key = parse_abc(abc_text)
    
    # 楽譜内にトークンがあるか確認
    if not TOKEN_PATTERN.search(music_content):
        return False
        
    print(f"-> 楽譜解析完了: Key={key}, Tempo={tempo}, Default Length={default_length}")
    samples = generate_samples(music_content, default_length, tempo, key)
    
    if not samples:
        return False
        
    save_wav(samples, output_wav)
    play_wav(output_wav)
    return True
