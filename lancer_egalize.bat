@echo off
REM Lance l'application EGALIZE et l'ouvre dans le navigateur (http://localhost:8501).
REM Laissez cette fenetre ouverte pendant l'utilisation ; fermez-la pour arreter l'application.
cd /d "%~dp0"
python -m streamlit run streamlit_app.py --server.port 8501
pause
