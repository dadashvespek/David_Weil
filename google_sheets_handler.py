import pygsheets
import pandas as pd
from pygsheets.exceptions import SpreadsheetNotFound

def send_results_to_sheets(passed_certs, failed_certs, user_email):
    # Authorization
    gc = pygsheets.authorize(service_file='future-datum-432413-b9-41e0f202bcba.json')

    sheet_name = 'QA Bot Results'

    try:
        # Try to open the Google spreadsheet
        sh = gc.open(sheet_name)
        print(f"Opened existing sheet: {sheet_name}")
    except SpreadsheetNotFound:
        # If the sheet doesn't exist, create it
        sh = gc.create(sheet_name)
        print(f"Created new sheet: {sheet_name}")
    
    # Share the sheet with the user's personal account
    sh.share(user_email, role='writer', type='user')
    print(f"Shared sheet with {user_email}")

    # Select the first sheet
    wks = sh[0]

    # Create dataframes for passed and failed certificates
    passed_df = pd.DataFrame([(eq_type, cert_no) for eq_type, certs in passed_certs.items() for cert_no in certs],
                             columns=['Equipment Type', 'Certificate Number'])
    passed_df['Status'] = 'Passed'

    failed_df = pd.DataFrame([(eq_type, cert['CertNo'], ', '.join(cert['Errors']))
                              for eq_type, certs in failed_certs.items() for cert in certs],
                             columns=['Equipment Type', 'Certificate Number', 'Errors'])
    failed_df['Status'] = 'Failed'

    # Combine the dataframes
    results_df = pd.concat([passed_df, failed_df], ignore_index=True)

    # Clear the existing content and update the sheet with the new dataframe
    wks.clear()
    wks.set_dataframe(results_df, (1, 1))

    print(f"Results have been sent to Google Sheets successfully.")
    print(f"Sheet URL: {sh.url}")
    return sh.url