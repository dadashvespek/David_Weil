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
    params = [
        {"EquipmentType": "IR Temp", "ProcedureCode": "DR-WI-0077"},
        {"EquipmentType": "Ambient Temp/Hum", "ProcedureCode": "DR-WI-0078"},
        {"EquipmentType": "scales", "ProcedureCode": "DR-WI-0126"},
        {"EquipmentType": "", "ProcedureCode": "", "UseTemplate": "True"},
        {"EquipmentType": "", "ProcedureCode": "", "UsePipetteModule": "True"},
        {"EquipmentType": "", "ProcedureCode": "", "HasAttachments": "True"}
    ]

    # Ensure the 'inputjson' directory exists
    input_dir = './inputjson'
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)

    # Proceed with data retrieval
    for param in params:
        data_response = requests.post(data_url, headers=headers, json=param)
        data = data_response.json()
        all_data.append(data)

        # Save individual JSON files
        if param.get("EquipmentType"):
            # If EquipmentType is not empty, use it in the file name
            file_name = f"data_response_{param['EquipmentType'].replace('/', '_')}.json"
        elif param.get("UseTemplate") == "True":
            file_name = "data_response_UseTemplate_True.json"
        elif param.get("UsePipetteModule") == "True":
            file_name = "data_response_UsePipetteModule_True.json"
        elif param.get("HasAttachments") == "True":
            file_name = "data_response_HasAttachment_True.json"
        else:
            file_name = "data_response_Unknown.json"

        file_path = os.path.join(input_dir, file_name)
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)

    return all_data
