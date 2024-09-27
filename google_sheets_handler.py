import pygsheets
import pandas as pd
from pygsheets.exceptions import SpreadsheetNotFound, WorksheetNotFound
from datetime import datetime

def send_results_to_sheets(passed_certs_main, failed_certs_main, passed_certs_pressure, failed_certs_pressure, user_email, sheet_name="QA Bot Results"):
    # Authorization
    gc = pygsheets.authorize(service_file='future-datum-432413-b9-ac007fce6dab.json')

    # Sheet name
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
    sheets = ["Passed Certificates", "Failed Certificates - Front Page",
              "Failed Certificates - Datasheet", "Failed Certificates - Template Status",
              "Pressure Certificates"]
    worksheets = {}
    for ws_name in sheets:
        try:
            worksheets[ws_name] = sh.worksheet_by_title(ws_name)
        except WorksheetNotFound:
            worksheets[ws_name] = sh.add_worksheet(ws_name)

    # Current date
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Initialize data lists
    passed_data = []
    failed_front_page_data = []
    failed_datasheet_data = []
    failed_template_status_data = []
    pressure_data = []  # Only for failed pressure certificates

    # Process passed main certificates
    for eq_type, certs in passed_certs_main.items():
        for cert in certs:
            cert_no = cert['CertNo']
            cal_date = cert.get('CalDate', '')
            data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'CalDate': cal_date,
                'Status': 'Passed',
                'Errors': '',
                'Test Date': current_date
            }
            passed_data.append(data)

    # Process passed pressure certificates (add to passed_data)
    for eq_type, certs in passed_certs_pressure.items():
        for cert in certs:
            cert_no = cert['CertNo']
            cal_date = cert.get('CalDate', '')
            data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'CalDate': cal_date,
                'Status': 'Passed',
                'Errors': '',
                'Test Date': current_date
            }
            passed_data.append(data)

    # Process failed main certificates
    for eq_type, certs in failed_certs_main.items():
        for cert in certs:
            cert_no = cert['CertNo']
            cal_date = cert.get('CalDate', '')
            cert_data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'CalDate': cal_date,
                'Status': 'Failed',
                'Errors': '',
                'Test Date': current_date
            }

            errors = cert['Errors']
            error_messages = []

            # Process different types of errors
            if errors.get('FrontPageErrors'):
                error_messages.append('Front Page Errors: ' + ', '.join(errors['FrontPageErrors']))
            if errors.get('AdditionalFieldsErrors'):
                error_messages.append('Additional Fields Errors: ' + ', '.join(errors['AdditionalFieldsErrors']))
            if errors.get('TemplateStatusError'):
                error_messages.append('Template Status Error: ' + errors['TemplateStatusError'])
            if errors.get('DatasheetErrors'):
                for group in errors['DatasheetErrors']:
                    group_name = group['Group']
                    for error in group['Errors']:
                        error_msg = f"Group: {group_name}, Row ID: {error['RowId']}, Error: {error['Error']}"
                        error_messages.append(error_msg)
            if errors.get('UnexpectedError'):
                error_messages.append('Unexpected Error: ' + '; '.join(errors['UnexpectedError']))

            if error_messages:
                cert_data['Errors'] = '; '.join(error_messages)
            else:
                cert_data['Errors'] = 'Unknown Error'

            failed_front_page_data.append(cert_data.copy())

    # Process failed pressure certificates
    for eq_type, certs in failed_certs_pressure.items():
        for cert in certs:
            cert_no = cert['CertNo']
            cal_date = cert.get('CalDate', '')
            cert_data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'CalDate': cal_date,
                'Status': 'Failed',
                'Errors': '',
                'Test Date': current_date
            }

            errors = cert['Errors']
            error_messages = []

            # Extract and process datasheet errors
            datasheet_errors = errors.get('DatasheetErrors', [])
            if datasheet_errors:
                for group in datasheet_errors:
                    group_name = group['Group']
                    for error in group['Errors']:
                        error_msg = f"Group: {group_name}, Row ID: {error['RowId']}, Error: {error['Error']}"
                        error_messages.append(error_msg)

            # If there are any error messages, join them into a single string
            if error_messages:
                cert_data['Errors'] = '; '.join(error_messages)
            else:
                cert_data['Errors'] = 'Unknown Error'

            # Append the certificate data to pressure_data
            pressure_data.append(cert_data.copy())

    # Write passed certificates
    passed_ws = worksheets["Passed Certificates"]
    passed_ws.clear()
    if passed_data:
        passed_df = pd.DataFrame(passed_data)
        # Convert "CalDate" to datetime
        passed_df['CalDate'] = pd.to_datetime(passed_df['CalDate'], errors='coerce')
        # Sort by "CalDate" descending
        passed_df = passed_df.sort_values(by='CalDate', ascending=False)
        passed_ws.set_dataframe(passed_df, (1, 1))

    # Write failed certificates (Front Page)
    if failed_front_page_data:
        ws = worksheets["Failed Certificates - Front Page"]
        ws.clear()
        failed_front_page_df = pd.DataFrame(failed_front_page_data)
        failed_front_page_df['CalDate'] = pd.to_datetime(failed_front_page_df['CalDate'], errors='coerce')
        failed_front_page_df = failed_front_page_df.sort_values(by='CalDate', ascending=False)
        ws.set_dataframe(failed_front_page_df, (1, 1))

    if failed_datasheet_data:
        ws = worksheets["Failed Certificates - Datasheet"]
        ws.clear()
        failed_datasheet_df = pd.DataFrame(failed_datasheet_data)
        ws.set_dataframe(failed_datasheet_df, (1, 1))

    if failed_template_status_data:
        ws = worksheets["Failed Certificates - Template Status"]
        ws.clear()
        failed_template_status_df = pd.DataFrame(failed_template_status_data)
        ws.set_dataframe(failed_template_status_df, (1, 1))

    # If there are errors not categorized above
    # At the point where you assign 'Unknown Error'
    if not cert_data['Errors']:
        print(f"Debug: No errors found in formatted_errors for certificate {cert_no}: {cert['Errors']}")
        cert_data['Errors'] = 'Unknown Error'
        failed_front_page_data.append(cert_data.copy())

    # Write failed pressure certificates
    pressure_ws = worksheets["Pressure Certificates"]
    pressure_ws.clear()
    if pressure_data:
        pressure_df = pd.DataFrame(pressure_data)
        pressure_df['CalDate'] = pd.to_datetime(pressure_df['CalDate'], errors='coerce')
        pressure_df = pressure_df.sort_values(by='CalDate', ascending=False)
        pressure_ws.set_dataframe(pressure_df, (1, 1))

    print(f"Results have been sent to Google Sheets successfully.")
    print(f"Sheet URL: {sh.url}")
    return sh.url