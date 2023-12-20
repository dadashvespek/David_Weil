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
    try:
        if value.lower() =='n/a':
            return 0
    except:pass
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

    try:
        numeric_value = float(value)
    except ValueError:
        raise ValueError(f"Value '{value}' is not a number and cannot be converted to grams.")

    return numeric_value * unit_converters.get(unit, 1)

def convert_to_psig(value, unit):

    atmospheric_pressure_psi = 14.7
    atmospheric_pressure_mmHg = 760

    unit_converters = {
        'mmHg g': 0.0193368,
        'mmHg': 0.0193368,
        'bar': 14.5038,
        'psi': 1,
        'psig': 1,
        'psia': lambda psia: psia - atmospheric_pressure_psi,
        'inH2O g': 0.0361,
        'inH2O': 0.0361,
        'inHg g': 0.4912,
        'MPa g': 145.038,
        'mmHg a': lambda mmHg_a: (mmHg_a - atmospheric_pressure_mmHg) * 0.0193368, 
        'kPa g': 0.145038
    }

    try:
        numeric_value = float(value)
    except ValueError:
        raise ValueError(f"Value '{value}' is not a number and cannot be converted to psig.")

    converter = unit_converters.get(unit)
    if callable(converter):  # Check if the converter is a function
        return converter(numeric_value)
    else:
        return numeric_value * converter

