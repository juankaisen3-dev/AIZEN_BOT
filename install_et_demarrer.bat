@echo off
echo ===================================================
echo     Installation des dependances pour Aizen_bot
echo ===================================================
echo.

python -m pip install -U -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] L'installation a echoue. Assurez-vous que Python est bien installe sur votre PC.
    pause
    exit /b %errorlevel%
)

echo.
echo ===================================================
echo     Demarrage du bot Aizen...
echo ===================================================
echo.

python bot.py
pause
