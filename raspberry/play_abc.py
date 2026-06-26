#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC記法の曲ファイルを読み込んで演奏するスクリプト
"""
import sys
import os

# 同一階層の abc_synthesizer をインポートできるように設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    import abc_synthesizer
except ImportError:
    print("エラー: abc_synthesizer.py が同じディレクトリに見つかりません。")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("使い方:")
        print("  python3 play_abc.py <楽譜のファイルパスまたはABCテキスト>")
        print("\n例:")
        print("  python3 play_abc.py \"X:1\\nM:4/4\\nK:C\\nC D E F | G A B c\"")
        sys.exit(1)
        
    arg = sys.argv[1]
    
    if os.path.exists(arg):
        # ファイルから読み込み
        with open(arg, 'r', encoding='utf-8', errors='ignore') as f:
            abc_text = f.read()
        print(f"ファイル '{arg}' から楽譜を読み込みました。")
    else:
        # 引数の文字列を直接ABCテキストとして扱う
        abc_text = arg
        print("引数で指定されたテキストから楽譜を読み込みました。")
        
    print("演奏を開始します...")
    success = abc_synthesizer.play_abc_string(abc_text)
    if success:
        print("演奏完了！")
    else:
        print("エラー: 楽譜の解析または演奏に失敗しました。ABCの構文を確認してください。")


if __name__ == "__main__":
    main()
