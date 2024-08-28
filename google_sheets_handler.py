import pygsheets
import pandas as pd
from pygsheets.exceptions import SpreadsheetNotFound, WorksheetNotFound

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

    # Create or clear sheets
    sheets = ["Passed Certificates", "Failed Certificates - Front Page", "Failed Certificates - Datasheet"]
    for sheet_name in sheets:
        try:
            worksheet = sh.worksheet_by_title(sheet_name)
            worksheet.clear()
        except WorksheetNotFound:
            sh.add_worksheet(sheet_name)

    # Passed Certificates
    passed_data = [(eq_type, cert_no) for eq_type, certs in passed_certs.items() for cert_no in certs]
    passed_df = pd.DataFrame(passed_data, columns=['Equipment Type', 'Certificate Number'])
    sh.worksheet_by_title("Passed Certificates").set_dataframe(passed_df, (1, 1))

    # Failed Certificates
    front_page_fails = []
    datasheet_fails = []

    for eq_type, certs in failed_certs.items():
        for cert in certs:
            front_page_errors = cert['Errors'].get('FrontPageErrors', [])
            additional_fields_errors = cert['Errors'].get('AdditionalFieldsErrors', [])
            datasheet_errors = cert['Errors'].get('DatasheetErrors', [])

            if front_page_errors or additional_fields_errors:
                front_page_fails.append({
                    'Equipment Type': eq_type,
                    'Certificate Number': cert['CertNo'],
                    'Front Page Errors': ', '.join(front_page_errors),
                    'Additional Fields Errors': ', '.join(additional_fields_errors)
                })

            if datasheet_errors:
                for group in datasheet_errors:
                    for error in group['Errors']:
                        datasheet_fails.append({
                            'Equipment Type': eq_type,
                            'Certificate Number': cert['CertNo'],
                            'Group': group['Group'],
                            'Row ID': error['RowId'],
                            'Error': error['Error']
                        })

    if front_page_fails:
        front_page_df = pd.DataFrame(front_page_fails)
        sh.worksheet_by_title("Failed Certificates - Front Page").set_dataframe(front_page_df, (1, 1))

    if datasheet_fails:
        datasheet_df = pd.DataFrame(datasheet_fails)
        sh.worksheet_by_title("Failed Certificates - Datasheet").set_dataframe(datasheet_df, (1, 1))

    print(f"Results have been sent to Google Sheets successfully.")
    print(f"Sheet URL: {sh.url}")
    return sh.url