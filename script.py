import json
import os
import re
from collections import defaultdict
from google_sheets_handler import send_results_to_sheets

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

def parse_numeric_value(value):
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None

def check_front_page(data):
    required_fields = [
        "CertNo", "CustomerCode", "EquipmentType", "AssetDescription",
        "Manufacturer", "Model", "OperatingRange", "AccreditationInfo"
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

def check_certificate(cert_data):
    env_conditions = check_environmental_conditions(cert_data)
    front_page_check, front_page_missing = check_front_page(cert_data)
    accreditation = check_accreditation(cert_data)
    tur_check, tur_values = check_tur(cert_data)
    additional_fields_check, missing_fields = check_additional_fields(cert_data)

    results = {
        "environmental_conditions": env_conditions,
        "front_page_complete": (front_page_check, front_page_missing),
        "accreditation": accreditation,
        "tur": (tur_check, tur_values),
        "additional_fields": (additional_fields_check, missing_fields)
    }
    
    return results


def retrieve_data():
    all_data = []
    input_dir = './inputjson'
    file_patterns = [
        'data_response_IR Temp.json',
        'data_response_Ambient Temp_Hum.json',
        'data_response_scales.json'
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

def check_certificate(cert_data):
    print(f"\nChecking certificate: {cert_data.get('CertNo', 'Unknown')}")
    print(f"Equipment Type: {cert_data.get('EquipmentType', 'Unknown')}")

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

    results = {
        "environmental_conditions": env_conditions,
        "front_page_complete": (front_page_check, front_page_missing),
        "accreditation": accreditation,
        "tur": (tur_check, tur_values),
        "additional_fields": (additional_fields_check, missing_fields)
    }
    
    return results

def main(all_data):
    passed_certs = defaultdict(list)
    failed_certs = defaultdict(list)

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
                result = check_certificate(cert)
                cert_no = cert.get("CertNo", "Unknown")
                equipment_type = cert.get("EquipmentType", "Unknown")
                
                if all(value if isinstance(value, bool) else value[0] for value in result.values()):
                    passed_certs[equipment_type].append(cert_no)
                    print(f"Certificate {cert_no} passed all checks")
                else:
                    errors = []
                    for key, value in result.items():
                        if isinstance(value, tuple):
                            if not value[0] and value[1]:
                                errors.append(f"{key}: {', '.join(value[1])}")
                        elif not value:
                            errors.append(key)
                    if errors:
                        failed_certs[equipment_type].append({"CertNo": cert_no, "Errors": errors})
                        print(f"Certificate {cert_no} failed checks: {', '.join(errors)}")
            except Exception as e:
                cert_no = cert.get("CertNo", "Unknown")
                equipment_type = cert.get("EquipmentType", "Unknown")
                failed_certs[equipment_type].append({"CertNo": cert_no, "Errors": [f"Unexpected error: {str(e)}"]})
                print(f"Unexpected error processing certificate {cert_no}: {str(e)}")

    # Send results to Google Sheets
    user_email = "zakirzhangozin@gmail.com"  # Replace with your actual email
    sheet_url = send_results_to_sheets(passed_certs, failed_certs, user_email)
    print(f"You can access the Google Sheet at: {sheet_url}")

    return passed_certs, failed_certs

# Retrieve data from local files
all_data = retrieve_data()

# Process the JSON data
passed_certs, failed_certs = main(all_data)

print("\nSummary:")
print(f"Passed certificates: {sum(len(certs) for certs in passed_certs.values())}")
print(f"Failed certificates: {sum(len(certs) for certs in failed_certs.values())}")

# Write results to files
with open('passed_certificates.txt', 'w') as f:
    f.write("Certificates that passed all checks:\n")
    if not any(passed_certs.values()):
        f.write("\nNo certificates passed all checks.\n")
    else:
        for equipment_type, certs in passed_certs.items():
            if certs:
                f.write(f"\nEquipment Type: {equipment_type}\n")
                for cert in certs:
                    f.write(f"{cert}\n")

with open('failed_certificates.txt', 'w') as f:
    f.write("Certificates that failed one or more checks:\n")
    if not any(failed_certs.values()):
        f.write("\nNo certificates failed any checks.\n")
    else:
        for equipment_type, certs in failed_certs.items():
            if certs:
                f.write(f"\nEquipment Type: {equipment_type}\n")
                for cert in certs:
                    f.write(f"Certificate: {cert['CertNo']}\n")
                    f.write(f"Errors: {', '.join(cert['Errors'])}\n\n")

print(f"Results have been written to 'passed_certificates.txt' and 'failed_certificates.txt'")