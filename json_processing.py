import json
import os

def save_json(data, name, folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, f"{name}.json")
    if isinstance(data, list):
        prepared_data = [json.loads(item) if isinstance(item, str) else item for item in data]
    else:
        prepared_data = data
    with open(file_path, 'w') as file:
        json.dump(prepared_data, file, indent=4)

    print(f"File '{name}.json' saved in '{folder_path}'.")

def convert_to_grams(value, unit):
    """
    Convert different mass units to grams.
    """
    unit_converters = {
        'µg': 1e-6,
        'mg': 1e-3,
        'g': 1,
        'kg': 1e3,
        'lb': 453.592 
    }
    return value * unit_converters.get(unit, 1) 