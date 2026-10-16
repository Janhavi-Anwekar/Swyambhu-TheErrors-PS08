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
- **AI Model:** Qwen3 4B (or a supported fallback model)
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

For the primary model:

```bash
ollama pull qwen3:4b
```

Optional smaller fallback model:

```bash
ollama pull qwen3:1.7b
```

Confirm that the model is available:

```bash
ollama list
```

The fallback model must also be configured in the application if the code is expected to use it automatically.

## Run the Application

From the project root directory, run:

```bash
streamlit run app/app.py
```

Streamlit will display a local URL in the terminal. Open that URL in your browser to access the dashboard.

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

This is the intended project structure. Update the tree to reflect the files actually present in the repository.

## AI Model

- **Model:** Qwen3 4B
- **Runtime:** Ollama
- **Execution:** Locally on the user's machine
- **Parameters:** Approximately 4 billion
- **Fallback:** Qwen3 1.7B, if configured and supported by the application
- **Model License:** Verify the exact model's license on its official model page before redistribution or deployment.

Official references:

- Ollama: https://ollama.com/
- Qwen3 4B: https://ollama.com/library/qwen3:4b
- Qwen3 1.7B: https://ollama.com/library/qwen3:1.7b

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

Contributions are welcome. Please use feature branches, test changes before submitting them, and describe the purpose and behavior of your changes in the pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
