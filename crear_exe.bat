@echo off
REM ==== Crea el juego en dist\SimuladorEspacial\SimuladorEspacial.exe ====
REM Ponlo en la misma carpeta que main.py (junto a images, sonidos, Fondo...). Ejecutalo en Windows.

pip install pyinstaller pygame opencv-python

set DATOS=--add-data "images;images"
if exist sonidos set DATOS=%DATOS% --add-data "sonidos;sonidos"
if exist sounds set DATOS=%DATOS% --add-data "sounds;sounds"
if exist audio set DATOS=%DATOS% --add-data "audio;audio"
if exist Fondo set DATOS=%DATOS% --add-data "Fondo;Fondo"
if exist "planeta rotando.mp4" set DATOS=%DATOS% --add-data "planeta rotando.mp4;."

REM Quita --windowed si quieres ver errores en una consola mientras pruebas
pyinstaller --noconfirm --clean --onedir --windowed --name SimuladorEspacial %DATOS% main.py

echo.
echo Listo. Prueba: dist\SimuladorEspacial\SimuladorEspacial.exe
echo Para compartirlo, comprime en ZIP toda la carpeta dist\SimuladorEspacial
pause
