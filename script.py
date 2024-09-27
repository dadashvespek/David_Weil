import json
import os
import re
import traceback
from collections import defaultdict
from data_retriever import retrieve_data
from google_sheets_handler import send_results_to_sheets
from pressure_cert_processor import retrieve_pressure_data, process_pressure_certificates
import sys

# Redirect stdout to a file
sys.stdout = open('script_output.txt', 'w')

def parse_numeric_value(value):
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = re.sub(r'[^\d.-]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def check_environmental_conditions(data):
    temp = data.get("EnvironmentalTemperature", "")
    humidity = data.get("EnvironmentalRelativeHumidity", "")
    
    # Remove only the degree symbol
    temp = temp.replace("\u00b0", "").strip()
    
    # Check if temperature is in Celsius or Fahrenheit
    if temp.endswith('C'):
        temp_c = parse_numeric_value(temp[:-1])
        temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
    elif temp.endswith('F'):
        temp_f = parse_numeric_value(temp[:-1])
        temp_c = (temp_f - 32) * 5/9 if temp_f is not None else None
    else:
        # If no unit is specified, try to parse as is
        temp_f = parse_numeric_value(temp)
        temp_c = (temp_f - 32) * 5/9 if temp_f is not None else None

    humidity_pct = parse_numeric_value(humidity.replace("%RH", "").strip())
    
    temp_check = (60 <= temp_f <= 100) if temp_f is not None else (15 <= temp_c <= 40 if temp_c is not None else False)
    humidity_check = 30 <= humidity_pct <= 80 if humidity_pct is not None else False
    
    return temp_check and humidity_check

def check_front_page(data):
    required_fields = [
        "CertNo", "CustomerCode", "EquipmentType", "AssetDescription",
        "Manufacturer", "Model", "OperatingRange", "AccreditationInfo", "EquipmentLocation"
    ]
    is_accredited = data.get("IsAccredited", False)
    if is_accredited:
        required_fields.extend(["Procedures", "Standards"])
    
    missing_fields = [field for field in required_fields if not data.get(field)]
    return len(missing_fields) == 0, missing_fields

def check_accreditation(data):
    is_accredited = data.get("IsAccredited", False)
    if not is_accredited:
        return True

    for group in data.get("Datasheet", []):
        for measurement in group.get("Measurements", []):
            meas_uncert = measurement.get("MeasUncert")
            if meas_uncert not in [None, "", "**"]:
                uncert_value = parse_numeric_value(meas_uncert)
                if uncert_value is not None:
                    return True
    
    # Check for alternative conditions
    if data.get("HasAttachment") and "External Certificate" in data.get("AttachmentType", []):
        return True
    if data.get("HasModule/Wizard"):
        return True

    return False

def check_customer_requirements_for_tur(data):
    customer_requirements = data.get("CustomerRequirements", [])
    return any("#CalibrationReqs: TUR Requerido: 4:1" in req for req in customer_requirements)

def check_tur(data):
    if not check_customer_requirements_for_tur(data):
        return True, []  # TUR check is not required, so it passes by default

    low_tur_values = []
    for group in data.get("Datasheet", []):
        for measurement in group.get("Measurements", []):
            tur = measurement.get("TUR", "")
            if tur and ":" in tur:
                ratio_str, _ = tur.split(":")
                ratio = parse_numeric_value(ratio_str)
                if ratio is not None and ratio < 4:
                    low_tur_values.append(tur)
    return len(low_tur_values) == 0, low_tur_values

def check_additional_fields(data):
    required_fields = {
        "CalDate": lambda d: any(std.get("CalDate") for std in d.get("Standards", [])),
        "DueDate": lambda d: any(std.get("DueDate") for std in d.get("Standards", []))
    }
    
    missing_fields = [field for field, check in required_fields.items() if not check(data)]
    return len(missing_fields) == 0, missing_fields

def check_template_status(data):
    return data.get("TemplateUsedStatus") == "Not Edited"

def check_certificate(cert_data):
    print(f"\nChecking certificate: {cert_data.get('CertNo', 'Unknown')}")
    print(f"Equipment Type: {cert_data.get('EquipmentType', 'Unknown')}")

    # Determine if this certificate uses a template
    is_template_cert = cert_data.get("TemplateUsed") is not None

    env_conditions = check_environmental_conditions(cert_data)
    print(f"Environmental conditions check: {env_conditions}")

    front_page_check, front_page_missing = check_front_page(cert_data)
    print(f"Front page check: {front_page_check}, Missing: {front_page_missing}")

    accreditation = check_accreditation(cert_data)
    print(f"Accreditation check: {accreditation}")

    tur_check, tur_values = check_tur(cert_data)
    print(f"TUR check: {tur_check}, Values: {tur_values}")

    additional_fields_check, missing_fields = check_additional_fields(cert_data)
    print(f"Additional fields check: {additional_fields_check}, Missing: {missing_fields}")

    template_status = True
    if is_template_cert:
        template_status = check_template_status(cert_data)
        print(f"Template status check: {template_status}")

    results = {
        "environmental_conditions": env_conditions,
        "front_page_complete": (front_page_check, front_page_missing),
        "accreditation": accreditation,
        "tur": (tur_check, tur_values),
        "additional_fields": (additional_fields_check, missing_fields),
        "template_status": template_status
    }

    formatted_errors = format_errors(results, cert_data, is_template_cert)
    return results, formatted_errors

def local_retrieve_data():
    retrieve_data()
    all_data = []
    input_dir = './inputjson'
    file_patterns = [
        'data_response_IR Temp.json',
        'data_response_Ambient Temp_Hum.json',
        'data_response_scales.json',
        'data_response_UseTemplate_True.json'
    ]

    for file_name in file_patterns:
        file_path = os.path.join(input_dir, file_name)
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                all_data.append(data)
                print(f"Successfully loaded data from {file_name}")
                print(f"Number of certificates in {file_name}: {len(data) if isinstance(data, list) else 1}")
        except FileNotFoundError:
            print(f"Warning: File '{file_path}' not found.")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in file '{file_path}'.")

    return all_data

def format_errors(result, cert_data, is_template_cert):
    formatted_errors = {
        "FrontPageErrors": [],
        "AdditionalFieldsErrors": [],
        "DatasheetErrors": [],
        "TemplateStatusError": None
    }

    print(f"\nFormatting errors for certificate: {cert_data.get('CertNo', 'Unknown')}")
    print(f"Result: {result}")
    print(f"Is Template Cert: {is_template_cert}")

    # Process front page errors
    if not result["front_page_complete"][0]:
        formatted_errors["FrontPageErrors"].extend(result["front_page_complete"][1])

    # Process accreditation error
    if not result["accreditation"]:
        formatted_errors["FrontPageErrors"].append("AccreditationInfo")

    # Process additional fields errors
    if not result["additional_fields"][0]:
        formatted_errors["AdditionalFieldsErrors"].extend(result["additional_fields"][1])

    # Process TUR errors
    if not result["tur"][0]:
        for group in cert_data.get("Datasheet", []):
            group_errors = []
            for measurement in group.get("Measurements", []):
                tur = measurement.get("TUR", "")
                if tur and ":" in tur:
                    ratio_str, _ = tur.split(":")
                    ratio = parse_numeric_value(ratio_str)
                    if ratio is not None and ratio < 4:
                        group_errors.append({
                            "RowId": measurement["RowId"],
                            "Error": f"Low TUR: {tur}"
                        })
            if group_errors:
                formatted_errors["DatasheetErrors"].append({
                    "Group": group["Group"],
                    "Errors": group_errors
                })

    # Process environmental conditions error
    if not result["environmental_conditions"]:
        formatted_errors["FrontPageErrors"].append("EnvironmentalConditions")

    # Corrected template status error condition
    if is_template_cert and not result["template_status"]:
        formatted_errors["TemplateStatusError"] = "Template has been edited"

    print(f"Formatted Errors: {formatted_errors}")

    return formatted_errors



def main(all_data):
    passed_certs_main = defaultdict(list)
    failed_certs_main = defaultdict(list)

    for data_set in all_data:
        if isinstance(data_set, list):
            certs = data_set
        elif isinstance(data_set, dict):
            certs = [data_set]
        else:
            print(f"Skipping invalid data set: {data_set}")
            continue

        print(f"\nProcessing {len(certs)} certificates")

        for cert in certs:
            try:
                result, formatted_errors = check_certificate(cert)
                cert_no = cert.get("CertNo", "Unknown")
                cal_date = cert.get("CalDate", "")
                equipment_type = cert.get("EquipmentType", "Unknown")

                # Check if all results are True or (True, [])
                if all(value if isinstance(value, bool) else value[0] for value in result.values()):
                    passed_certs_main[equipment_type].append({
                        "CertNo": cert_no,
                        "CalDate": cal_date
                    })
                    print(f"Certificate {cert_no} passed all checks")
                else:
                    failed_certs_main[equipment_type].append({
                        "CertNo": cert_no,
                        "CalDate": cal_date,
                        "Errors": formatted_errors
                    })
                    print(f"Certificate {cert_no} failed checks: {formatted_errors}")
                    
            except Exception as e:
                cert_no = cert.get("CertNo", "Unknown")
                cal_date = cert.get("CalDate", "")
                equipment_type = cert.get("EquipmentType", "Unknown")
                error_message = f"{str(e)}\n{traceback.format_exc()}"
                failed_certs_main[equipment_type].append({
                    "CertNo": cert_no,
                    "CalDate": cal_date,
                    "Errors": {"UnexpectedError": [error_message]}
                })
                print(f"Unexpected error processing certificate {cert_no}: {error_message}")

    # Process pressure certificates
    pressure_data = retrieve_pressure_data()
    if pressure_data is not None:
        passed_certs_pressure, failed_certs_pressure = process_pressure_certificates()
    else:
        print("Skipping pressure certificate processing due to retrieval error.")
        passed_certs_pressure = defaultdict(list)
        failed_certs_pressure = defaultdict(list)

    # Send results to Google Sheets
    user_email = "zakirzhangozin@gmail.com"  # Replace with your actual email
    sheet_url = send_results_to_sheets(passed_certs_main, failed_certs_main, passed_certs_pressure, failed_certs_pressure, user_email)
    print(f"You can access the Google Sheet at: {sheet_url}")

    return passed_certs_main, failed_certs_main, passed_certs_pressure, failed_certs_pressure

# Retrieve data from local files
all_data = local_retrieve_data()

# Process the JSON data
passed_certs_main, failed_certs_main, passed_certs_pressure, failed_certs_pressure = main(all_data)

# Reset stdout to default
sys.stdout.close()
sys.stdout = sys.__stdout__

print("\nSummary:")
total_passed = sum(len(certs) for certs in passed_certs_main.values()) + sum(len(certs) for certs in passed_certs_pressure.values())
total_failed = sum(len(certs) for certs in failed_certs_main.values()) + sum(len(certs) for certs in failed_certs_pressure.values())
print(f"Passed certificates: {total_passed}")
print(f"Failed certificates: {total_failed}")

# Write results to files
with open('passed_certificates.txt', 'w') as f:
    f.write("Certificates that passed all checks:\n")
    if not any(passed_certs_main.values()) and not any(passed_certs_pressure.values()):
        f.write("\nNo certificates passed all checks.\n")
    else:
        # Write main passed certificates
        for equipment_type, certs in passed_certs_main.items():
            if certs:
                f.write(f"\nEquipment Type: {equipment_type}\n")
                for cert in certs:
                    f.write(f"{cert}\n")
        # Write pressure passed certificates
        for equipment_type, certs in passed_certs_pressure.items():
            if certs:
                f.write(f"\nEquipment Type: {equipment_type}\n")
                for cert in certs:
                    f.write(f"{cert}\n")

with open('failed_certificates.txt', 'w') as f:
    f.write("Certificates that failed one or more checks:\n")
    if not any(failed_certs_main.values()) and not any(failed_certs_pressure.values()):
        f.write("\nNo certificates failed any checks.\n")
    else:
        # Write main failed certificates
        for equipment_type, certs in failed_certs_main.items():
            if certs:
                f.write(f"\nEquipment Type: {equipment_type}\n")
                for cert in certs:
                    f.write(f"Certificate: {cert['CertNo']}\n")
                    errors = cert['Errors']
                    if errors.get("FrontPageErrors"):
                        f.write("Front Page Errors: " + ", ".join(errors["FrontPageErrors"]) + "\n")
                    if errors.get("AdditionalFieldsErrors"):
                        f.write("Additional Fields Errors: " + ", ".join(errors["AdditionalFieldsErrors"]) + "\n")
                    if errors.get("DatasheetErrors"):
                        f.write("Datasheet Errors:\n")
                        for group in errors["DatasheetErrors"]:
                            f.write(f"  Group: {group['Group']}\n")
                            for error in group['Errors']:
                                f.write(f"    Row {error['RowId']}: {error['Error']}\n")
                    f.write("\n")
        # Write pressure failed certificates
        for equipment_type, certs in failed_certs_pressure.items():
            if certs:
                f.write(f"\nEquipment Type: {equipment_type}\n")
                for cert in certs:
                    f.write(f"Certificate: {cert['CertNo']}\n")
                    errors = cert['Errors']
                    if errors.get("DatasheetErrors"):
                        f.write("Datasheet Errors:\n")
                        for group in errors["DatasheetErrors"]:
                            f.write(f"  Group: {group['Group']}\n")
                            for error in group['Errors']:
                                f.write(f"    Row {error['RowId']}: {error['Error']}\n")
                    f.write("\n")

print(f"Results have been written to 'passed_certificates.txt' and 'failed_certificates.txt'")
