import requests
import os
import json

def retrieve_data():
    auth_url = "http://calsystem-temp.azurewebsites.net/api/auth/login"
    auth_data = {
        "UserName": "calsystest@phoenixcalibrationdr.com",
        "Password": "Phoenix1234@+"
    }

    # Authenticate and get token
    response = requests.post(auth_url, json=auth_data)
    response_data = response.json()
    token = response_data.get("AccessToken")['Token']

    # Data retrieval endpoint
    data_url = "http://calsystem-temp.azurewebsites.net/api/Calibration/GetCertificatesDataListByEquipmentType"
    headers = {'Authorization': f'Bearer {token}'}

    all_data = []
    equipment_types = [
        {"EquipmentType": "IR Temp", "ProcedureCode": "DR-WI-0077"},
        {"EquipmentType": "Ambient Temp/Hum", "ProcedureCode": "DR-WI-0078"},
        {"EquipmentType": "scales", "ProcedureCode": "DR-WI-0126"}
    ]

    for params in equipment_types:
        data_response = requests.post(data_url, headers=headers, json=params)
        data = data_response.json()
        all_data.append(data)

        # Save individual JSON files
        file_name = f"data_response_{params['EquipmentType'].replace('/', '_')}.json"
        file_path = os.path.join("./inputjson", file_name)
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)

    return all_data