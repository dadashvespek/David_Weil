import pygsheets
import pandas as pd
from pygsheets.exceptions import SpreadsheetNotFound, WorksheetNotFound
from datetime import datetime

def send_results_to_sheets(passed_certs_main, failed_certs_main, passed_certs_pressure, failed_certs_pressure, user_email, sheet_name="QA Bot Results"):
    # Authorization
    gc = pygsheets.authorize(service_file='future-datum-432413-b9-41e0f202bcba.json')

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
              "Scales Certificates", "Pressure Certificates"]
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
    scales_data = []
    pressure_data = []

    # Process passed main certificates
    for eq_type, certs in passed_certs_main.items():
        for cert_no in certs:
            data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'Status': 'Passed',
                'Errors': '',
                'Test Date': current_date
            }
            if eq_type.lower() == "scales":
                scales_data.append(data)
            else:
                passed_data.append(data)

    # Process passed pressure certificates
    for eq_type, certs in passed_certs_pressure.items():
        for cert_no in certs:
            data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'Status': 'Passed',
                'Errors': '',
                'Test Date': current_date
            }
            pressure_data.append(data)

    # Process failed main certificates
    for eq_type, certs in failed_certs_main.items():
        for cert in certs:
            cert_no = cert['CertNo']
            cert_data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'Status': 'Failed',
                'Errors': '',
                'Test Date': current_date
            }

            # Initialize a set to track unique errors
            unique_errors = set()

            front_page_errors = cert['Errors'].get('FrontPageErrors', [])
            additional_fields_errors = cert['Errors'].get('AdditionalFieldsErrors', [])
            datasheet_errors = cert['Errors'].get('DatasheetErrors', [])
            template_status_error = cert['Errors'].get('TemplateStatusError', '')

            # Process front page and additional field errors
            if front_page_errors or additional_fields_errors:
                error_msg = ''
                if front_page_errors:
                    error_msg += 'Front Page Errors: ' + ', '.join(front_page_errors)
                if additional_fields_errors:
                    error_msg += '; Additional Fields Errors: ' + ', '.join(additional_fields_errors)
                cert_data['Errors'] = error_msg
                if eq_type.lower() == "scales":
                    scales_data.append(cert_data.copy())
                else:
                    failed_front_page_data.append(cert_data.copy())

            # Process datasheet errors
            if datasheet_errors:
                for group in datasheet_errors:
                    group_name = group['Group']
                    for error in group['Errors']:
                        error_msg = f"Group: {group_name}, Row ID: {error['RowId']}, Error: {error['Error']}"
                        if error_msg not in unique_errors:
                            unique_errors.add(error_msg)
                            cert_data_copy = cert_data.copy()
                            cert_data_copy['Errors'] = error_msg
                            if eq_type.lower() == "scales":
                                scales_data.append(cert_data_copy)
                            else:
                                failed_datasheet_data.append(cert_data_copy)

            # Process template status errors
            if template_status_error:
                cert_data['Errors'] = f"Template Status Error: {template_status_error}"
                if eq_type.lower() == "scales":
                    scales_data.append(cert_data.copy())
                else:
                    failed_template_status_data.append(cert_data.copy())

            # If there are errors not categorized above
            if not cert_data['Errors']:
                cert_data['Errors'] = 'Unknown Error'
                if eq_type.lower() == "scales":
                    scales_data.append(cert_data.copy())
                else:
                    failed_front_page_data.append(cert_data.copy())

    # Process failed pressure certificates
    for eq_type, certs in failed_certs_pressure.items():
        for cert in certs:
            cert_no = cert['CertNo']
            cert_data = {
                'Equipment Type': eq_type,
                'Certificate Number': cert_no,
                'Status': 'Failed',
                'Errors': '',
                'Test Date': current_date
            }

            # Initialize a set to track unique errors
            unique_errors = set()

            # Extract errors
            datasheet_errors = cert['Errors'].get('DatasheetErrors', [])

            # Process datasheet errors
            if datasheet_errors:
                for group in datasheet_errors:
                    group_name = group['Group']
                    for error in group['Errors']:
                        error_msg = f"Group: {group_name}, Row ID: {error['RowId']}, Error: {error['Error']}"
                        if error_msg not in unique_errors:
                            unique_errors.add(error_msg)
                            cert_data_copy = cert_data.copy()
                            cert_data_copy['Errors'] = error_msg
                            pressure_data.append(cert_data_copy)

            # If there are errors not categorized above
            if not cert_data['Errors']:
                cert_data['Errors'] = 'Unknown Error'
                pressure_data.append(cert_data.copy())

    # Write passed certificates (non-scales, non-pressure)
    passed_ws = worksheets["Passed Certificates"]
    passed_ws.clear()
    if passed_data:
        passed_df = pd.DataFrame(passed_data)
        passed_ws.set_dataframe(passed_df, (1, 1))

    # Write failed certificates (non-scales, non-pressure)
    if failed_front_page_data:
        ws = worksheets["Failed Certificates - Front Page"]
        ws.clear()
        failed_front_page_df = pd.DataFrame(failed_front_page_data)
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

    # Write scales certificates
    scales_ws = worksheets["Scales Certificates"]
    scales_ws.clear()
    if scales_data:
        scales_df = pd.DataFrame(scales_data)
        scales_ws.set_dataframe(scales_df, (1, 1))

    # Write pressure certificates
    pressure_ws = worksheets["Pressure Certificates"]
    pressure_ws.clear()
    if pressure_data:
        pressure_df = pd.DataFrame(pressure_data)
        pressure_ws.set_dataframe(pressure_df, (1, 1))

    print(f"Results have been sent to Google Sheets successfully.")
    print(f"Sheet URL: {sh.url}")
    return sh.url
