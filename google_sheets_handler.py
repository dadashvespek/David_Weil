import pygsheets
import pandas as pd
from pygsheets.exceptions import SpreadsheetNotFound, WorksheetNotFound
from datetime import datetime

def send_results_to_sheets(passed_certs, failed_certs, user_email):
    # Authorization
    gc = pygsheets.authorize(service_file='future-datum-432413-b9-41e0f202bcba.json')

    sheet_name = 'QA Bot Results'

    try:
        sh = gc.open(sheet_name)
        print(f"Opened existing sheet: {sheet_name}")
    except SpreadsheetNotFound:
        sh = gc.create(sheet_name)
        print(f"Created new sheet: {sheet_name}")

    sh.share(user_email, role='writer', type='user')
    print(f"Shared sheet with {user_email}")

    # Get or create worksheets
    sheets = ["Passed Certificates", "Failed Certificates - Front Page", "Failed Certificates - Datasheet", "Failed Certificates - Template Status"]
    worksheets = {}
    for sheet_name in sheets:
        try:
            worksheets[sheet_name] = sh.worksheet_by_title(sheet_name)
        except WorksheetNotFound:
            worksheets[sheet_name] = sh.add_worksheet(sheet_name)

    # Current date
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Process passed certificates
    passed_ws = worksheets["Passed Certificates"]
    passed_data = []
    for eq_type, certs in passed_certs.items():
        for cert_no in certs:
            passed_data.append({
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'Test Date': current_date
            })
    passed_df = pd.DataFrame(passed_data)
    passed_ws.clear()
    if not passed_df.empty:
        passed_ws.set_dataframe(passed_df, (1,1))

    # Process failed certificates
    for sheet_name in ["Failed Certificates - Front Page", "Failed Certificates - Datasheet", "Failed Certificates - Template Status"]:
        ws = worksheets[sheet_name]
        ws.clear()
        failed_data = []

        for eq_type, certs in failed_certs.items():
            for cert in certs:
                if sheet_name == "Failed Certificates - Front Page":
                    front_page_errors = cert['Errors'].get('FrontPageErrors', [])
                    additional_fields_errors = cert['Errors'].get('AdditionalFieldsErrors', [])
                    if front_page_errors or additional_fields_errors:
                        failed_data.append({
                            'Equipment Type': eq_type,
                            'Certificate Number': cert['CertNo'],
                            'Front Page Errors': ', '.join(front_page_errors),
                            'Additional Fields Errors': ', '.join(additional_fields_errors),
                            'Test Date': current_date
                        })
                elif sheet_name == "Failed Certificates - Datasheet":
                    datasheet_errors = cert['Errors'].get('DatasheetErrors', [])
                    for group in datasheet_errors:
                        for error in group['Errors']:
                            failed_data.append({
                                'Equipment Type': eq_type,
                                'Certificate Number': cert['CertNo'],
                                'Group': group['Group'],
                                'Row ID': error['RowId'],
                                'Error': error['Error'],
                                'Test Date': current_date
                            })
                elif sheet_name == "Failed Certificates - Template Status":
                    template_status_error = cert['Errors'].get('TemplateStatusError')
                    if template_status_error:
                        failed_data.append({
                            'Equipment Type': eq_type,
                            'Certificate Number': cert['CertNo'],
                            'Template Status Error': template_status_error,
                            'Test Date': current_date
                        })

        if failed_data:
            failed_df = pd.DataFrame(failed_data)
            ws.set_dataframe(failed_df, (1,1))

    print(f"Results have been sent to Google Sheets successfully.")
    print(f"Sheet URL: {sh.url}")
    return sh.url