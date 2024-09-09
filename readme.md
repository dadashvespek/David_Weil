# QA Bot Script

This script processes calibration certificates, performs quality checks, and reports the results to Google Sheets.

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- Git (optional, for cloning the repository)

## Checking Python Installation

1. Open a command prompt or terminal.
2. Run the following command:
   ```
   python --version
   ```
3. If Python is installed, you'll see the version number. If not, you'll need to install Python from [python.org](https://www.python.org/downloads/).

## Setting Up the Project

1. Clone the repository or download the project files to your local machine.

2. Navigate to the project directory in your command prompt or terminal.

3. Create a virtual environment:
   ```
   python -m venv venv
   ```

4. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

5. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Project Structure

Ensure your project directory has the following structure:
```
project_directory/
│
├── data_retriever.py
├── script.py
├── google_sheets_handler.py
├── requirements.txt
├── future-datum-432413-b9-41e0f202bcba.json
│
└── inputjson/
    ├── data_response_IR Temp.json
    ├── data_response_Ambient Temp_Hum.json
    └── data_response_scales.json
```

## Running the Script

1. Ensure your virtual environment is activated.

2. Run the main script:
   ```
   python script.py
   ```

3. The script will process the certificates, perform quality checks, and send the results to Google Sheets.

4. Check the console output for the Google Sheets URL where you can view the results.

## Output

The script generates two local output files:
- `passed_certificates.txt`: Lists certificates that passed all checks.
- `failed_certificates.txt`: Lists certificates that failed one or more checks, with details on the failures.

Results are also sent to a Google Sheets document, which will be shared with the link below.

https://docs.google.com/spreadsheets/d/1_ExYBvkxhFVpOXXL8-0uC4scSGNxFGA3pPLripKonJA/edit?usp=sharing

## Troubleshooting

- If you encounter any "module not found" errors, ensure you've activated the virtual environment and installed all requirements.
- For issues related to Google Sheets integration, verify that the `future-datum-432413-b9-41e0f202bcba.json` file is present in the project directory and contains valid credentials.
- If the script can't find the input JSON files, make sure they are correctly placed in the `inputjson` directory.
