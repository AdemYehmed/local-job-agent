@echo off
REM ============================================================
REM  MiniLLM JobAgent - lancement du frontend sous Windows
REM  Sert le dossier courant sur http://localhost:5500
REM  (le backend reste sur http://127.0.0.1:8000, inchange)
REM ============================================================
cd /d "%~dp0"
title MiniLLM frontend - port 5500

where python >nul 2>nul
if errorlevel 1 goto try_py

echo Serveur local: http://localhost:5500/home.html
echo Fermez cette fenetre (ou Ctrl+C) pour arreter.
start "" http://localhost:5500/home.html
python -m http.server 5500
goto end

:try_py
where py >nul 2>nul
if errorlevel 1 goto no_python
echo Serveur local: http://localhost:5500/home.html
start "" http://localhost:5500/home.html
py -m http.server 5500
goto end

:no_python
echo Python n'a pas ete trouve.
echo Ouverture directe des fichiers (mode degrade : les appels API
echo peuvent etre bloques par le navigateur - voir README.md).
start "" "%~dp0home.html"
pause

:end
