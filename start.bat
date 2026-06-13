@echo off
chcp 65001 > nul
title CodeChat

echo ================================
echo   CodeChat を起動します
echo ================================

:: サーバーを別ウィンドウで起動（起動済みなら python がエラーで終了するだけ）
start "CodeChat Server" python "%~dp0server.py"

:: サーバーが立ち上がるまで待機
echo   起動待機中...
timeout /t 3 /nobreak > nul

:: ブラウザを開く
echo   ブラウザを開きます ^^ http://localhost:3000
start "" "http://localhost:3000"
