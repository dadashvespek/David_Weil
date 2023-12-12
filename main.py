from json_processing import save_json
import json
import glob
import os
import math
from termcolor import colored
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

os.makedirs('Final_Results', exist_ok=True)
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


def check_measurement_uncertainty_nested(json_data_list, certification):

    results_by_certno = {} 
    for json_data in json_data_list:
        datasheets = json_data.get("Datasheet", [])
        CertNo = json_data.get("CertNo", "Unknown CertNo")
        print(colored(f"CertNo: {CertNo}", "blue"))

        results = [] 

        for datasheet in datasheets:
            group = datasheet.get("Group", "Unknown Group")
            measurements = datasheet.get("Measurements", [])

            for measurement in measurements:
                nominal = measurement.get("Nominal")
                meas_uncert_str = measurement.get("MeasUncert")
                if meas_uncert_str in ["n/a", "N/A", '**', '**\nn/a', "''", ''] or meas_uncert_str is None:
                    continue

                meas_uncert = convert_to_grams(float(meas_uncert_str), measurement.get("MeasUnit"))

                if meas_uncert != 'n/a':
                    for range_info in certification["measurement_uncertainty"]:
                        nominal_value = float(nominal)
                        nominal_value = convert_to_grams(nominal_value, measurement.get("Units"))
                        test_nominal_value = nominal_value *0.99

                        if range_info["range"][0] <= test_nominal_value <= range_info["range"][1]:
                            fixed_uncertainty = convert_to_grams(range_info["fixed_uncertainty"], range_info["fixed_uncertainty_unit"])
                            variable_uncertainty_per_unit = convert_to_grams(range_info["variable_uncertainty"], range_info["variable_uncertainty_unit"].split('/')[0])
                            per_unit = range_info["variable_uncertainty_unit"].split('/')[1]

                            if per_unit != 'g':
                                if any(char.isdigit() for char in per_unit):
                                    conversion_factor = convert_to_grams(int(per_unit.split(' ')[0]), per_unit.split(' ')[1])
                                else:
                                    conversion_factor = convert_to_grams(1, per_unit)

                                variable_uncertainty_per_unit = variable_uncertainty_per_unit / conversion_factor

                            variable_uncertainty = variable_uncertainty_per_unit * nominal_value
                            total_uncertainty = fixed_uncertainty + variable_uncertainty
                            scale = 10 ** (1 - int(math.floor(math.log10(abs(total_uncertainty)))))
                            total_uncertainty = round(total_uncertainty * scale) / scale

                            passed = meas_uncert >= total_uncertainty
                            status = "Passed" if passed else "Failed"
                            color = "green" if passed else "red"
                            if status == "Failed":
                                result = {
                                    "group": group,
                                    "nominal": f"{nominal_value}g",
                                    "measured_uncertainty": f"{meas_uncert}g",
                                    "required_uncertainty": f"{total_uncertainty}g",
                                    "passed": passed
                                }
                                print(colored(f"[{status}] Group: {group}, Nominal: {nominal_value}g, Measured Uncertainty: {meas_uncert}g, Required Uncertainty: {total_uncertainty}g", color))
                                results.append(result)

        if results:
            results_by_certno[CertNo] = results

    return results_by_certno  




list_of_all_json = glob.glob(os.path.join('inputjson', '*.json'))
for i,ajson in enumerate(list_of_all_json):
    final_results = check_measurement_uncertainty_nested(json.load(open(list_of_all_json[0], 'r', encoding='utf-8')), json.load(open('certjson.json','r', encoding='utf-8')))
    save_json(final_results, f'final_{i}','Final_Results')

