# pressure_cert_processor.py

from collections import defaultdict
import os
import json
import glob
import requests


def convert_to_psig(value, unit):
    """Converts a pressure value to psig based on the unit."""
    # Implement the actual conversion logic based on your requirements
    conversion_factors = {
        'psi': 1,
        'psig': 1,
        'psia': lambda x: x - 14.7,  # Example adjustment for atmospheric pressure
    }
    if unit in conversion_factors:
        factor = conversion_factors[unit]
        if callable(factor):
            return factor(value)
        else:
            return value * factor
    else:
        raise ValueError(f"Unsupported unit: {unit}")
    
def retrieve_pressure_data():
    auth_url = "http://calsystem-temp.azurewebsites.net/api/auth/login"
    auth_data = {
        "UserName": "calsystest@phoenixcalibrationdr.com",
        "Password": "Phoenix1234@+"
    }

    # Authenticate and get token
    response = requests.post(auth_url, json=auth_data)

    # Check if authentication was successful
    if response.status_code != 200:
        print(f"Authentication failed with status code {response.status_code}")
        print(f"Response text: {response.text}")
        return None

    try:
        response_data = response.json()
        token = response_data.get("AccessToken", {}).get('Token')
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError during authentication: {e}")
        print(f"Response text: {response.text}")
        return None

    if not token:
        print("Authentication failed: No token received")
        return None

    # Data retrieval endpoint
    data_url = "http://calsystem-temp.azurewebsites.net/api/Calibration/GetCertificatesDataListByEquipmentType"
    headers = {'Authorization': f'Bearer {token}'}
    data_params = {
        "EquipmentType": "scales",
        "ProcedureCode": "DR-WI-0126"
    }

    # Make the data request
    data_response = requests.post(data_url, headers=headers, json=data_params)

    # Check if the response is successful
    if data_response.status_code != 200:
        print(f"Data request failed with status code {data_response.status_code}")
        print(f"Response text: {data_response.text}")
        return None

    try:
        data = data_response.json()
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError during data retrieval: {e}")
        print(f"Response text: {data_response.text}")
        return None

    # Proceed if data is successfully retrieved
    dir_name = "./pressure_input_jsons"
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    file_name = "pressure_data_response.json"
    file_path = os.path.join(dir_name, file_name)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
    return data

def is_valid_float(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False

# Function to convert units (implement as needed)
def convert_to_psig(value, unit):
    # Implement the actual conversion logic based on your requirements
    conversion_factors = {
        'psi': 1,
        'psig': 1,
        'psia': lambda x: x - 14.7,  # Example adjustment for atmospheric pressure
        # Add other units and their conversion logic
    }
    if unit in conversion_factors:
        factor = conversion_factors[unit]
        if callable(factor):
            return factor(value)
        else:
            return value * factor
    else:
        raise ValueError(f"Unsupported unit: {unit}")
    
def convert_to_grams(value, unit):
    # Implement unit conversion logic as needed
    unit = unit.lower()
    if unit == 'g':
        return value
    elif unit == 'mg':
        return value / 1000
    elif unit == 'kg':
        return value * 1000
    elif unit == 'lb':
        return value * 453.59237
    elif unit == 'n/a':
        return value * 0
    elif unit == '%':
        return value * 0.01
    elif unit == '°c':
        return value * 0
    else:
        raise ValueError(f"Unsupported unit: {unit}")
    
def process_pressure_certificates():
    # Exclusion list (if any)
    exclusion_list = []

    # Define the required directions and their corresponding group parts
    split_directions = {
        'UP': ['up', 'ascendente'],
        'DOWN': ['down', 'dw', 'dn', 'descendente']
    }

    # Percentage thresholds (adjust as needed)
    lower_percent_of_max_rep = 0.4
    upper_percent_of_max_rep = 1.0
    lower_percent_of_max_ecce = 0.4
    upper_percent_of_max_ecce = 1.0


    list_of_all_json = glob.glob(os.path.join('pressure_input_jsons', '*.json'))
    if not list_of_all_json:
        print("No JSON files found in pressure_input_jsons directory.")
        return defaultdict(list), defaultdict(list)

    # Load the certificate data
    with open(list_of_all_json[0], 'r', encoding='utf-8') as f:
        json_data_list = json.load(f)

    # Initialize dictionaries to store passed and failed certificates
    passed_certs = defaultdict(list)
    failed_certs = defaultdict(list)

    for json_data in json_data_list:
        equipment_type = "Scales & Balances"
        dict_of_noms = {}
        group_values = []
        results = []
        datasheets = json_data.get("Datasheet", [])
        certno = json_data.get("CertNo", "Unknown CertNo")
        equipment_type = json_data.get("EquipmentType", "Unknown")
        asset_description = json_data.get("AssetDescription", "Unknown AssetDescription")
        excluded = any(keyword in asset_description.lower() for keyword in exclusion_list)
        certno = json_data.get("CertNo", "Unknown CertNo")
        cal_date = json_data.get("CalDate", "")
        customer_code = json_data.get("CustomerCode", "Unknown")

        print(f"Processing CertNo: {certno}, Equipment Type: {equipment_type}")

        # Ensure CalibrationResult is "Limited" for On-Site Calibration
        if json_data.get("CalLocation", "") == "On-Site Calibration" and json_data.get("CalibrationResult", "") != "Limited":
            json_data["CalibrationResult"] = "Limited"

        std_present = False
        nominal_std = 0
        unitofnominal = 'g'

        # Initialize total_measurements_up_dw before using it
        total_measurements_up_dw = []

        # Check for the presence of 'std' or 'desviación' groups
        for datasheet in datasheets:
            group = datasheet.get("Group", "Unknown Group")
            group_values.append(group)

            if 'std' in group.lower() or 'desviación' in group.lower():
                std_present = True

            if group.split(' ')[-1].lower() in ['weight', 'peso'] or 'rep' in group.lower():
                measurements = datasheet.get("Measurements", [])
                nominal_values = []
                for i in measurements:
                    nominal_str = i.get("Nominal")
                    units = i.get("Units", 'g')
                    if nominal_str not in [None, '', 'N/A'] and is_valid_float(nominal_str):
                        nominal_value = float(nominal_str)
                        converted_nominal = convert_to_grams(nominal_value, units)
                        if converted_nominal is not None:
                            nominal_values.append(converted_nominal)
                        else:
                            print(f"Skipping measurement with unsupported unit '{units}' in certificate '{certno}'.")

                if nominal_values:
                    max_nominal_std = max(nominal_values)
                    nominal_std = max_nominal_std
                    unitofnominal = measurements[0].get("Units", 'g') if measurements else 'g'
                    dict_of_noms['Group - Repeatability'] = max_nominal_std
                else:
                    max_nominal_std = 0
                    nominal_std = 0
                    dict_of_noms['Group - Repeatability'] = max_nominal_std
                    print(f"No valid nominal values found in group '{group}' for certificate '{certno}'.")

        # Check for missing directions
        not_present = [direction for direction, parts in split_directions.items()
                       if not any(part.lower() in element.lower() for part in parts for element in group_values)]

        cert_passed = True  # Assume certificate passes unless an error is found
        cert_errors = {
            "DatasheetErrors": []
        }

        if not_present and not excluded:
            error_message = f"Directions not present: {not_present}"
            print(error_message)
            cert_passed = False
            cert_errors["DatasheetErrors"].append({
                "Group": "General",
                "Errors": [{
                    "RowId": "N/A",
                    "Error": error_message
                }]
            })

        if not std_present and not excluded:
            error_message = "No 'std' or 'desviación' group found"
            print(error_message)
            cert_passed = False
            cert_errors["DatasheetErrors"].append({
                "Group": "General",
                "Errors": [{
                    "RowId": "N/A",
                    "Error": error_message
                }]
            })

        # Now process datasheets again for other checks
        for datasheet in datasheets:
            group = datasheet.get("Group", "Unknown Group")
            measurements = datasheet.get("Measurements", [])

            if any(keyword in group.lower() for keyword in ['up', 'ascendente', 'down', 'dw', 'dn', 'descendente']):
                total_measurements_up_dw.append(len(measurements))

                # Update max_nominal calculation
                nominal_values = []
                for i in measurements:
                    nominal_str = i.get("Nominal")
                    units = i.get("Units", 'g')
                    if nominal_str not in [None, '', 'N/A'] and is_valid_float(nominal_str):
                        nominal_value = float(nominal_str)
                        converted_nominal = convert_to_grams(nominal_value, units)
                        if converted_nominal is not None:
                            nominal_values.append(converted_nominal)
                        else:
                            print(f"Skipping measurement with unsupported unit '{units}' in certificate '{certno}'.")


                if nominal_values:
                    max_nominal = max(nominal_values)
                    dict_of_noms['Weight - Linearity'] = max_nominal
                else:
                    max_nominal = 0
                    dict_of_noms['Weight - Linearity'] = max_nominal
                    print(f"No valid nominal values found in group '{group}' for certificate '{certno}'.")

            elif group.split(' ')[-1].lower() not in ['weight', 'peso'] and 'rep' not in group.lower():
                # Similar update for other groups
                nominal_values = []
                for i in measurements:
                    nominal_str = i.get("Nominal")
                    units = i.get("Units", 'g')
                    if nominal_str not in [None, '', 'N/A'] and is_valid_float(nominal_str):
                        nominal_value = float(nominal_str)
                        converted_nominal = convert_to_grams(nominal_value, units)
                        if converted_nominal is not None:
                            nominal_values.append(converted_nominal)
                        else:
                            print(f"Skipping measurement with unsupported unit '{units}' in certificate '{certno}'.")


                if nominal_values:
                    max_nominal = max(nominal_values)
                    dict_of_noms[group] = max_nominal
                else:
                    max_nominal = 0
                    dict_of_noms[group] = max_nominal
                    print(f"No valid nominal values found in group '{group}' for certificate '{certno}'.")

            for measurement in measurements:
                formatted_comment = measurement.get("FormattedComment", "")
                if formatted_comment:
                    comment_parts = formatted_comment.split('--')
                    if len(comment_parts) > 1:
                        comment_keyword = comment_parts[1]
                        if comment_keyword.lower().replace(" ", "") not in group.lower().replace(" ", ""):
                            error_message = f"RowId: {measurement.get('RowId')}: Formatted comment '{comment_keyword}' does not match the Group '{group}'"
                            print(error_message)
                            cert_passed = False
                            cert_errors["DatasheetErrors"].append({
                                "Group": group,
                                "Errors": [{
                                    "RowId": measurement.get("RowId", "Unknown RowId"),
                                    "Error": error_message
                                }]
                            })

        if len(total_measurements_up_dw) > 1:
            total_measures = sum(total_measurements_up_dw)
            if total_measures < 9:
                error_message = f"Number of measurements: {total_measures} is less than required 9"
                print(error_message)
                cert_passed = False
                cert_errors["DatasheetErrors"].append({
                    "Group": "General",
                    "Errors": [{
                        "RowId": "N/A",
                        "Error": error_message
                    }]
                })

        # Check nominal weights against thresholds
        max_linearity = dict_of_noms.get('Weight - Linearity', 0)
        for key, value in dict_of_noms.items():
            if (key.split(' ')[-1].lower() in ['weight', 'peso'] or 'rep' in key.lower()) and not excluded:
                if max_linearity == 0:
                    error_message = f"Max linearity is zero, cannot compute percentage thresholds for {key}"
                    print(error_message)
                    cert_passed = False
                    cert_errors["DatasheetErrors"].append({
                        "Group": key,
                        "Errors": [{
                            "RowId": "N/A",
                            "Error": error_message
                        }]
                    })
                elif not (lower_percent_of_max_rep * max_linearity <= value <= max_linearity * upper_percent_of_max_rep):
                    error_message = f"{key} with a maximum value of {value}g is not within {round(lower_percent_of_max_rep*100,1)}% to {round(upper_percent_of_max_rep*100)}% of max linearity {max_linearity}g"
                    print(error_message)
                    cert_passed = False
                    cert_errors["DatasheetErrors"].append({
                        "Group": key,
                        "Errors": [{
                            "RowId": "N/A",
                            "Error": error_message
                        }]
                    })

        if cert_passed:
            passed_certs[equipment_type].append({
                "CertNo": certno,
                "CalDate": cal_date,
                "CustomerCode": customer_code
            })
            print(f"Certificate {certno} passed all checks.")
        else:
            failed_certs[equipment_type].append({
                "CertNo": certno,
                "CalDate": cal_date,
                "CustomerCode": customer_code,
                "Errors": cert_errors
            })
            print(f"Certificate {certno} failed checks.")

    return passed_certs, failed_certs