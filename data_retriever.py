import json
import re

def parse_numeric_value(value):
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        # Remove any non-numeric characters except decimal point and minus sign
        cleaned = re.sub(r'[^\d.-]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def check_environmental_conditions(data):
    temp = data.get("EnvironmentalTemperature", "")
    humidity = data.get("EnvironmentalRelativeHumidity", "")
    
    temp_f = parse_numeric_value(temp)
    humidity_pct = parse_numeric_value(humidity)
    
    temp_check = 60 <= temp_f <= 100 if temp_f is not None else False
    humidity_check = 30 <= humidity_pct <= 80 if humidity_pct is not None else False
    
    return temp_check and humidity_check

def check_accreditation(data):
    is_accredited = data.get("IsAccredited", False)
    if not is_accredited:
        return False
    
    for group in data.get("Datasheet", []):
        for measurement in group.get("Measurements", []):
            meas_uncert = measurement.get("MeasUncert")
            if meas_uncert not in [None, "", "**"]:
                uncert_value = parse_numeric_value(meas_uncert)
                if uncert_value is not None:
                    return True
    return False

def check_tur(data):
    low_tur_values = []
    for group in data.get("Datasheet", []):
        for measurement in group.get("Measurements", []):
            tur = measurement.get("TUR", "")
            if tur and ":" in tur:
                ratio_str, _ = tur.split(":")
                ratio = parse_numeric_value(ratio_str)
                if ratio is not None and ratio < 4:
                    low_tur_values.append(tur)
    return low_tur_values

def check_certificate(cert_data):
    tur_values = check_tur(cert_data)
    results = {
        "environmental_conditions": check_environmental_conditions(cert_data),
        "accreditation": check_accreditation(cert_data),
        "tur": len(tur_values) == 0,
        "front_page_complete": all(cert_data.get(field) for field in [
            "CertNo", "CustomerCode", "EquipmentType", "AssetDescription",
            "Manufacturer", "Model", "OperatingRange", "AccreditationInfo"
        ]),
        "has_procedures": bool(cert_data.get("Procedures")),
        "has_standards": bool(cert_data.get("Standards")),
    }
    
    if not results["tur"]:
        results["tur_values"] = tur_values
    
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
            
            if all(key in ["tur", "tur_values"] or value for key, value in result.items()):
                passed_certs.append(cert_no)
            else:
                errors = []
                for key, value in result.items():
                    if key == "tur" and not value:
                        errors.append(f"tur: {', '.join(result['tur_values'])}")
                    elif not value and key != "tur_values":
                        errors.append(key)
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