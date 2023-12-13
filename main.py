from json_processing import save_json, convert_to_grams
import json
import glob
import os
import math
from termcolor import colored
from directions import split_directions


os.makedirs('Final_Results', exist_ok=True)

import re

def check_measurement_uncertainty_nested(json_data_list, certification):
    results_by_certno = {} 
    for json_data in json_data_list:
        group_values = []
        results = [] 
        datasheets = json_data.get("Datasheet", [])
        CertNo = json_data.get("CertNo", "Unknown CertNo")
        # print(colored(f"CertNo: {CertNo}", "blue"))
        std_passed = False
        for datasheet in datasheets:
            group = datasheet.get("Group", "Unknown Group")
            group_values.append(group)
            if 'std' in group.lower() or 'desviación' in group.lower():
    
                std_passed = True
                if std_passed:
                    int_var = int(''.join(re.findall(r'\d+', group))) if any(char.isdigit() for char in group) else False
                    if not int_var:
                        result = {
                            
                            "STD_Has_Weight": False,
                        }
                        # print(colored(f"[Failed] No std weight found", "red"))
                        results.append(result)
                    else:
                        std_value = int_var
                        print(colored(f"[Passed] STD weight found: {std_value}g", "green"))
            not_present = [direction for direction, parts in split_directions.items() if not any(part.lower() in element.lower() for part in parts for element in group_values)]
        if not_present != []:
            print(colored(f"CerNo: {CertNo}", "blue"))
            print(colored(f"Directions not present: {not_present}", "blue"))
            results.append({"Directions not present": not_present})

        if not std_passed:
            result ={
                "STD_Present": False,
            }
            print(colored(f"[Failed] No std group found", "red"))
            results.append(result)


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

                            weight_passed = meas_uncert >= total_uncertainty
                            status = "Passed" if weight_passed else "Failed"
                            color = "green" if weight_passed else "red"
                            if status == "Failed":
                                result = {
                                    "group": group,
                                    "nominal": f"{nominal_value}g",
                                    "measured_uncertainty": f"{meas_uncert}g",
                                    "required_uncertainty": f"{total_uncertainty}g",
                                    "weight_passed": weight_passed,

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

