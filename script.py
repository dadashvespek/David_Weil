import json
import re

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

def main(json_data):
    passed_certs = []
    failed_certs = []

    if isinstance(json_data, list):
        certs = json_data
    elif isinstance(json_data, dict):
        certs = [json_data]
    else:
        raise ValueError("Input must be a JSON object or array of objects")
    
    for cert in certs:
        try:
            result = check_certificate(cert)
            cert_no = cert.get("CertNo", "Unknown")
            
            if all(value if isinstance(value, bool) else value[0] for value in result.values()):
                passed_certs.append(cert_no)
            else:
                errors = []
                for key, value in result.items():
                    if key == "tur":
                        if not value[0]:
                            errors.append(f"tur: {', '.join(value[1])}")
                    elif key == "additional_fields":
                        if not value[0] and value[1]:  # Only add if there are actually missing fields
                            errors.append(f"missing fields: {', '.join(value[1])}")
                    elif key == "front_page_complete":
                        if not value[0]:
                            errors.append(f"front page incomplete: {', '.join(value[1])}")
                    elif not value:
                        errors.append(key)
                if errors:  # Only add to failed_certs if there are actual errors
                    failed_certs.append({"CertNo": cert_no, "Errors": errors})
        except Exception as e:
            cert_no = cert.get("CertNo", "Unknown")
            failed_certs.append({"CertNo": cert_no, "Errors": [f"Unexpected error: {str(e)}"]})
    
    return passed_certs, failed_certs

# Read JSON data from file
file_path = './inputjson/data_response1.json'
try:
    with open(file_path, 'r') as file:
        json_data = json.load(file)
except FileNotFoundError:
    print(f"Error: File '{file_path}' not found.")
    exit(1)
except json.JSONDecodeError:
    print(f"Error: Invalid JSON in file '{file_path}'.")
    exit(1)

# Process the JSON data
passed_certs, failed_certs = main(json_data)

# Write results to files
with open('passed_certificates.txt', 'w') as f:
    f.write("Certificates that passed all checks:\n")
    for cert in passed_certs:
        f.write(f"{cert}\n")

with open('failed_certificates.txt', 'w') as f:
    f.write("Certificates that failed one or more checks:\n")
    for cert in failed_certs:
        f.write(f"Certificate: {cert['CertNo']}\n")
        f.write(f"Errors: {', '.join(cert['Errors'])}\n\n")

print(f"Results have been written to 'passed_certificates.txt' and 'failed_certificates.txt'")