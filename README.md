# AquaMind V0.1

Prueba de concepto para priorizar inspecciones en redes hidráulicas con datos sintéticos.

## Ejecutar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/generate_data.py
python -m streamlit run app.py
```

Luego abre `http://localhost:8501`.

## Importante

Esta versión no es machine learning ni un detector de fugas validado. El índice es un baseline heurístico y explicable para probar el flujo de decisión. Los datos son sintéticos y los pesos son provisionales.
