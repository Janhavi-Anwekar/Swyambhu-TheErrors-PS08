# Config Drift Detector

An AI-assisted configuration drift detection platform that identifies servers whose configurations differ from an approved fleet baseline, evaluates potential risks, and explains detected changes using a locally running open-weight AI model.

## Features

- **Configuration Drift Detection:** Identifies differences between approved baseline configurations and current configurations.
- **Fleet-Based Scanning:** Supports configuration analysis across multiple server profiles.
- **Risk Scoring:** Evaluates detected changes using predefined security rules and risk scores.
- **AI-Powered Explanations:** Uses a local Qwen model through Ollama to explain detected drift and suggest possible fixes.
- **Interactive Dashboard:** Displays configuration findings and scan results through Streamlit.
- **Scan Reports:** Saves scan results for later review and analysis.
- **Automated Testing:** Tests whether deliberately introduced configuration changes are detected correctly.
- **Modular Architecture:** Separates data collection, detection, risk rules, AI explanations, and dashboard components.

## Tech Stack

- **Programming Language:** Python
- **Dashboard:** Streamlit
- **Local AI Runtime:** Ollama
- **AI Model:** Qwen2.5 3B (`qwen2.5:3b`)
- **Configuration Data:** JSON and other explicitly supported configuration formats
- **Testing:** Python testing tools

## Setup

### Prerequisites

1. Install Python 3.11 or later.
2. Install Git.
3. Install Ollama.
4. Ensure the selected Qwen model is supported by your Ollama installation.

### Clone the Repository

```bash
git clone <repo-url>
cd config-drift-detector
```

Replace `<repo-url>` with your repository URL.

### Create and Activate a Virtual Environment

On Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, follow the Python virtual-environment instructions for your operating system.

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Download the AI Model

Download the model used by the application:

```bash
ollama pull qwen2.5:3b
```

Confirm that the model is available:

```bash
ollama list
```

The model identifier configured in the application must match the model installed in Ollama.

## Run the Application

From the project root directory, run:

```bash
streamlit run app/app.py
```

Streamlit will display a local URL in the terminal. Open that URL in your browser to access the dashboard.

> Ensure the application path matches the actual location of `app.py` in your repository.

## How It Works

1. **Load Configuration Data:** Read the available configuration data and approved baseline.
2. **Parse Settings:** Extract supported settings from the input using the appropriate parser.
3. **Compare Configurations:** Identify changed, missing, and newly added settings.
4. **Evaluate Risks:** Apply predefined rules to assess the potential impact of detected changes.
5. **Generate Explanations:** Use the local AI model to explain findings and suggest possible corrections.
6. **Display Results:** Present findings through the dashboard.
7. **Save Reports:** Store scan results for future review and comparison.

## Project Structure

```text
config-drift-detector/
├── fleet/
│   ├── generate_fleet.py
│   └── inject_drift.py
├── collector/
│   └── ...
├── engine/
│   └── ...
├── rules/
│   └── risky_settings.json
├── ai/
│   ├── mock.py
│   └── ...
├── app/
│   └── app.py
├── tests/
│   └── ...
├── docs/
│   └── samples/
├── requirements.txt
└── README.md
```

This is an illustrative project structure. Update it to reflect the files and directories actually present in the repository.

## AI Model

- **Model Provider:** Alibaba Cloud (Qwen)
- **Model:** Qwen2.5 3B
- **Model Identifier:** `qwen2.5:3b`
- **Runtime:** Ollama
- **Execution:** Locally on the user's machine
- **Parameters:** Approximately 3 billion
- **Model License:** Refer to the official model repository and model-provider terms for the applicable license.

### Official Model and License References

- **Ollama:** https://ollama.com/
- **Qwen2.5 3B on Ollama:** https://ollama.com/library/qwen2.5:3b
- **Qwen2.5 Official Repository and License:** https://github.com/QwenLM/Qwen2.5
- **Qwen Model Provider:** https://qwen.ai/

The AI model is a third-party component and is licensed separately from this project's source code. Review the applicable model license and terms of use before redistribution or deployment.

## Security Considerations

- Scan only systems and configuration files you are authorized to assess.
- Treat configuration files as potentially sensitive because they may contain internal infrastructure details.
- Avoid exposing credentials, private keys, tokens, or other secrets in scan reports or AI prompts.
- Review AI-generated explanations and recommendations before applying any changes.
- Do not interpret a risk score as a probability that an attack will occur.
- Unsupported directives and parsing limitations should be reported clearly.
- Do not automatically modify production configurations without an authorized, tested change-management process.

## Limitations

- Detection accuracy depends on the quality of the approved baseline, parsing logic, and security rules.
- Different configuration formats require their own parsers and validation rules.
- Some configurations contain defaults, included files, conditional sections, or other behavior that a basic parser may not fully interpret.
- AI-generated explanations may be incomplete or incorrect and should be validated.
- Features such as Docker collection, multi-server scanning, and automated drift injection are available only when their corresponding modules are implemented.

## Testing

Run the project's tests using the test framework configured in the repository.

If the project uses pytest, install it if necessary and run:

```bash
python -m pytest
```

Tests should cover:

- Unchanged configurations.
- Changed settings.
- Missing settings.
- Newly added settings.
- Risk-rule evaluation.
- Invalid or unsupported configuration input.
- AI response validation and fallback behavior.

## Development Workflow

1. Create a separate feature branch.

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make changes within your assigned files or modules.
3. Run the relevant tests.
4. Commit your changes.

   ```bash
   git add .
   git commit -m "Add your feature description"
   ```

5. Push your branch.

   ```bash
   git push -u origin feature/your-feature-name
   ```

6. Open a pull request for review.

Avoid modifying the same files as another team member without coordinating first.

## Contributions

Contributions are welcome. Please use feature branches, test changes before submitting them, and describe the purpose and behavior of the changes in the pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

The project's MIT license applies to the project code covered by that license, not automatically to third-party AI models or dependencies.
