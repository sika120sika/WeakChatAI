@echo off
chcp 65001 > nul
title CodeChat

echo ================================
echo   CodeChat 起動中...
echo ================================

:: すでにポート3000が使用中か確認
netstat -ano | findstr ":3000 " | findstr "LISTENING" > nul 2>&1
if %errorlevel% == 0 (
    echo   サーバーはすでに起動しています
    goto OPEN
)

:: server.py を別ウィンドウで起動
start "CodeChat Server" python "%~dp0server.py"

:: サーバーが起動するまで待機（最大5秒）
set /a tries=0
:WAIT
timeout /t 1 /nobreak > nul
netstat -ano | findstr ":3000 " | findstr "LISTENING" > nul 2>&1
if %errorlevel% == 0 goto OPEN
set /a tries+=1
if %tries% lss 5 goto WAIT
echo   警告: サーバーの起動確認がタイムアウトしました

:OPEN
echo   ブラウザを開きます → http://localhost:3000
start "" http://localhost:3000
