from json_processing import save_json, convert_to_psig
import json
import glob
import os
from termcolor import colored

os.makedirs('Final_Results', exist_ok=True)
list_of_all_json = glob.glob(os.path.join('pressure_input_jsons', '*.json'))
json_data_list = json.load(open(list_of_all_json[0], 'r', encoding='utf-8'))
accreditation = json.load(open('pressurecert.json', 'r', encoding='utf-8'))
results = []

for i in json_data_list:
    certno = i.get("CertNo", "Unknown CertNo")
    print(colored(f"CertNo: {certno}", "green"))
    datasheets = i.get("Datasheet", "Unknown Datasheets")

    for d in datasheets:
        measurements = d.get("Measurements", "Unknown Measurements")

        for m in measurements:
            nominal_o = float(m.get("Nominal", "Unknown Nominal"))
            nominal = convert_to_psig(nominal_o, m.get("Units", "Unknown NominalUnit").split(" ")[0])
            nominal_unit = m.get("Units", "Unknown NominalUnit").split(" ")[0]

            try:
                measure_cert_o = float(m.get("MeasUncert", "Unknown Certainty"))
                measure_cert = convert_to_psig(measure_cert_o, m.get("MeasUnit", "Unknown CertaintyUnit").split(" ")[0])
                measure_cert_unit = m.get("MeasUnit", "Unknown CertaintyUnit").split(" ")[0] 
            except:
                continue

            smallest_required_uncertainty = float('inf')
            largest_uncertainty_range = None

            for range_info in accreditation["measurement_uncertainty"]:
                if range_info["range"][0] <= nominal <= range_info["range"][1]:
                    try:
                        variable_uncertainty = range_info["variable_uncertainty"]
                        variable_uncertainty_unit = range_info["variable_uncertainty_unit"]
                    except:
                        variable_uncertainty = 0
                        variable_uncertainty_unit = ""

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
                print(colored(f"Failed: {measure_cert} {measure_cert_unit} <= {smallest_required_uncertainty} {nominal_unit}", "red"))
                result = {
                    "CertNo": certno,
                    "Unconverted Nominal": f"{nominal_o} {nominal_unit}",
                    "Converted nominal": f"{nominal} psig",
                    "Required Uncertainty": smallest_required_uncertainty,
                    "Uncertainty Range": largest_uncertainty_range,
                    "Unconverted Measured Uncertainty": measure_cert_o,
                    "Converted Measured Uncertainty": measure_cert,
                    "Result": f"Failed because {smallest_required_uncertainty} > {measure_cert}"
                }
                results.append(result)

save_json(results, 'pressure_results', 'Final_Pressure_Results')
