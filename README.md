# config-drift-detector

Finds servers whose configuration has drifted from the fleet baseline,
and explains the drift using a local open-weight AI model.

## Setup
1. Install Python 3.11+ and Git
2. Clone the repo and open the folder
3. Create and activate a virtual environment:
   python -m venv venv
   venv\Scripts\activate
4. Install libraries: pip install -r requirements.txt
5. Install Ollama, then run: ollama pull qwen3:4b
   (fallback: ollama pull qwen3:1.7b)

## Run
streamlit run app/app.py


## AI Model
- Model: Qwen3 4B, run locally with Ollama
- Parameters: 4 billion
- Licence: Apache 2.0 (confirm on the model's page and link it here)

## Licence
MIT