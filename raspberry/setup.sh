#!/bin/bash
# 繝ｩ繧ｺ繝代う縺ｧ縺ｮ繧ｻ繝・ヨ繧｢繝・・

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo " 繝ｩ繧ｺ繝代う LLM 繧ｯ繝ｩ繧､繧｢繝ｳ繝・繧ｻ繝・ヨ繧｢繝・・"
echo "========================================"
echo "繝輔か繝ｫ繝: $SCRIPT_DIR"
echo ""
echo "縺薙・繝輔か繝ｫ繝縺ｮ荳ｭ霄ｫ:"
ls -la "$SCRIPT_DIR"
echo ""

# Windows謾ｹ陦・CRLF)繧帝勁蜴ｻ
for f in "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR"/*.py; do
    [ -f "$f" ] && sed -i 's/\r$//' "$f" 2>/dev/null
done

# config.py 縺後↑縺代ｌ縺ｰ閾ｪ蜍穂ｽ懈・
if [ ! -f "$SCRIPT_DIR/config.py" ]; then
    echo "[INFO] config.py 繧定・蜍穂ｽ懈・縺励∪縺・
    printf '%s\n' \
        'OLLAMA_HOST = "10.98.145.83"' \
        'OLLAMA_PORT = 11434' \
        'DEFAULT_MODEL = "qwen3.5:9b"' \
        > "$SCRIPT_DIR/config.py"
fi

# 蠢・医ヵ繧｡繧､繝ｫ遒ｺ隱搾ｼ亥､ｧ譁・ｭ怜ｰ乗枚蟄励・諡｡蠑ｵ蟄宣＆縺・ｂ謗｢縺呻ｼ・MISSING=0
for name in test_connection.py; do
    found=""
    for f in "$SCRIPT_DIR/$name" "$SCRIPT_DIR/${name%.py}.PY" "$SCRIPT_DIR/${name}.txt"; do
        if [ -f "$f" ]; then
            found="$f"
            break
        fi
    done
    if [ -n "$found" ]; then
        echo "[OK] $name"
    else
        echo "[NG] $name 縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "繝輔ぃ繧､繝ｫ縺ｯ隕九∴縺ｦ縺・ｋ縺ｮ縺ｫ NG 縺ｫ縺ｪ繧句ｴ蜷・"
    echo "  cd $SCRIPT_DIR"
    echo "  sed -i 's/\r$//' *.sh *.py"
    echo "  bash setup.sh"
    echo ""
    echo "縺ｾ縺溘・ setup.sh 繧剃ｽｿ繧上★逶ｴ謗･:"
    echo "  python3 $SCRIPT_DIR/test_connection.py"
    exit 1
fi

chmod +x "$SCRIPT_DIR/setup.sh" 2>/dev/null
chmod +x "$SCRIPT_DIR/test_connection.py"
chmod +x "$SCRIPT_DIR/play_abc.py"

MARKER="# ollama-remote-client"
if ! grep -q "$MARKER" "$HOME/.bashrc" 2>/dev/null; then
    cat >> "$HOME/.bashrc" << EOF

$MARKER
alias llm-test='python3 $SCRIPT_DIR/test_connection.py'
alias play-abc='python3 $SCRIPT_DIR/play_abc.py'
EOF
    echo ""
    echo "[OK] alias 繧・~/.bashrc 縺ｫ霑ｽ蜉縺励∪縺励◆"
else
    # 既存のエイリアスに play-abc を追加（ない場合のみ）
    if ! grep -q "alias play-abc" "$HOME/.bashrc" 2>/dev/null; then
        sed -i "/alias llm-test/a alias play-abc='python3 $SCRIPT_DIR/play_abc.py'" "$HOME/.bashrc"
    fi
    echo ""
    echo "[OK] alias 縺ｯ譌終險ｭ螳壽ｸ医∩縺ｧ縺・
fi

echo ""
echo "菴ｿ縺・婿:"
echo "  source ~/.bashrc"
echo "  llm-test"
echo ""
grep OLLAMA_HOST "$SCRIPT_DIR/config.py" 2>/dev/null || true
