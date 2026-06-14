@echo off
echo ============================================
echo  Clasificacion Historica - instalacion/arranque
echo ============================================
echo.
echo Instalando dependencias (esto puede tardar un poco la primera vez)...
python -m pip install -r requirements.txt

echo.
echo Arrancando la app...
python -m streamlit run app.py

pause
