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
    
def retrieve_pressure_data():
    auth_url = "http://portal.phoenixcalibrationdr.com/api/auth/login"
    auth_data = {
        "UserName": "calsystest@phoenixcalibrationdr.com",
        "Password": "Phoenix@1234#"
    }

    # Authenticate and get token
    response = requests.post(auth_url, json=auth_data)
    response_data = response.json()
    token = response_data.get("AccessToken")['Token']

    # Data retrieval endpoint
    data_url = "http://portal.phoenixcalibrationdr.com/api/Calibration/GetCertificatesDataListByEquipmentType"
    headers = {'Authorization': f'Bearer {token}'}
    data_params = {
        "EquipmentType": "scales",
        "ProcedureCode": "DR-WI-0126"
    }

    # Make the data request
    data_response = requests.post(data_url, headers=headers, json=data_params)
    data = data_response.json()

    dir_name = "./pressure_input_jsons"
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    file_name = "pressure_data_response.json"
    file_path = os.path.join(dir_name, file_name)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
    return data

def process_pressure_certificates():
    list_of_all_json = glob.glob(os.path.join('pressure_input_jsons', '*.json'))
    if not list_of_all_json:
        print("No JSON files found in pressure_input_jsons directory.")
        return defaultdict(list), defaultdict(list)
    json_data_list = json.load(open(list_of_all_json[0], 'r', encoding='utf-8'))
    accreditation = json.load(open('pressurecert.json', 'r', encoding='utf-8'))
    
    # Initialize dictionaries to store passed and failed certificates
    passed_certs = defaultdict(list)
    failed_certs = defaultdict(list)
    
    for i in json_data_list:
        certno = i.get("CertNo", "Unknown CertNo")
        equipment_type = i.get("EquipmentType", "Pressure")
        print(f"CertNo: {certno}")
        datasheets = i.get("Datasheet", [])
    
        for d in datasheets:
            measurements = d.get("Measurements", [])
    
            for m in measurements:
                # Implement your measurement processing and conversion logic here
                # For example:
                try:
                    nominal_o = float(m.get("Nominal"))
                    nominal_unit = m.get("Units").split(" ")[0]
                    nominal = convert_to_psig(nominal_o, nominal_unit)
                    
                    measure_cert_o = float(m.get("MeasUncert"))
                    measure_cert_unit = m.get("MeasUnit").split(" ")[0]
                    measure_cert = convert_to_psig(measure_cert_o, measure_cert_unit)
                except (TypeError, ValueError):
                    continue 
    
                smallest_required_uncertainty = float('inf')
                largest_uncertainty_range = None
    
                for range_info in accreditation["measurement_uncertainty"]:
                    if range_info["range"][0] <= nominal <= range_info["range"][1]:
                        variable_uncertainty = range_info.get("variable_uncertainty", 0)
                        variable_uncertainty_unit = range_info.get("variable_uncertainty_unit", "")
    
                        if variable_uncertainty_unit == "%":
                            variable_uncertainty = nominal * (float(variable_uncertainty)/100)
                        elif variable_uncertainty_unit == "μpsig/psig":
                            variable_uncertainty = float(variable_uncertainty) * nominal/10000
    
                        fixed_uncertainty = range_info["fixed_uncertainty"]
                        required_uncertainty = fixed_uncertainty + variable_uncertainty
    
                        if required_uncertainty < smallest_required_uncertainty:
                            smallest_required_uncertainty = round(required_uncertainty,7)
                            largest_uncertainty_range = range_info["range"]
    
                if measure_cert <= smallest_required_uncertainty * 0.98:
                    print(f"Failed: {measure_cert} {measure_cert_unit} <= {smallest_required_uncertainty} {nominal_unit}")
                    
                    # Add to failed_certs dictionary
                    failed_certs[equipment_type].append({
                        "CertNo": certno,
                        "Errors": {
                            "DatasheetErrors": [{
                                "Group": d.get("Group", "Unknown Group"),
                                "Errors": [{
                                    "RowId": m.get("RowId", "Unknown RowId"),
                                    "Error": f"Uncertainty too high: {measure_cert} <= {smallest_required_uncertainty}"
                                }]
                            }]
                        }
                    })
                else:
                    print(f"Passed: {measure_cert} {measure_cert_unit} > {smallest_required_uncertainty} {nominal_unit}")
                    
                    # Add to passed_certs dictionary
                    passed_certs[equipment_type].append(certno)
    
    return passed_certs, failed_certs
