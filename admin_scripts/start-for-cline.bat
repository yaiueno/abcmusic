@echo off
REM Cline 使う前にこれを実行。ウィンドウは閉じないでください。
REM ollama run と同じ — モデルをメモリに載せたまま固定
ollama run qwen3.6-long --keepalive -1
