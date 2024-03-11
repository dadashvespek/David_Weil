import requests
import os
import json

def retrieve_data():
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

    print(data)
    dir_name = "./inputjson"
    file_name = "data_response.json"
    file_path = os.path.join(dir_name, file_name)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
    file_path

    return data