from json_processing import save_json, convert_to_psig
import json
import glob
import os
import math
from termcolor import colored
from directions import split_directions
from fileprocessing import lower_percent_of_max_ecce, lower_percent_of_max_rep, upper_percent_of_max_ecce, upper_percent_of_max_rep, exclusion_list
from googlesearch import search
os.makedirs('Final_Results', exist_ok=True)
list_of_all_json = glob.glob(os.path.join('pressure_input_jsons', '*.json'))
json_data_list=json.load(open(list_of_all_json[0], 'r', encoding='utf-8'))
accreditation = json.load(open('pressurecert.json', 'r', encoding='utf-8'))
xunits= ['mmHg g', 'bar g', 'psi g', 'inH2O g', 'inHg g', 'MPa g', 'mmHg a', 'kPa g']
results = []
for i in json_data_list:
    certno=i.get("CertNo", "Unknown CertNo")
    print(colored(f"CertNo: {certno}", "green"))
    equiptype=i.get("EquipmentType", "Unknown EquipmentType")
    print(colored(f"EquipmentType: {equiptype}", "green"))
    datasheets = i.get("Datasheet", "Unknown Datasheets")
    for d in datasheets:
        groupname=d.get("Group", "Unknown GroupName")
        measurements = d.get("Measurements", "Unknown Measurements")
        for m in measurements:
            nominal = float(m.get("Nominal", "Unknown Nominal"))
            nominal_unit = m.get("Units", "Unknown NominalUnit").split(" ")[0]
            
            measure_cert = m.get("MeasUncert", "Unknown Certainty")
            measure_cert_unit = m.get("MeasUnit", "Unknown CertaintyUnit")
            try:
                float(measure_cert)
                is_measure_cert_valid_float = True
            except:
                is_measure_cert_valid_float = False
                continue

            if is_measure_cert_valid_float:
                measure_cert = float(measure_cert)
                measure_cert_unit = measure_cert_unit.split(" ")[0] 
                if measure_cert_unit == "bar" or measure_cert_unit == "psi":
                    nominal = convert_to_psig(nominal, nominal_unit)
                    nominal_unit = "psig"
                    measure_cert = convert_to_psig(measure_cert, measure_cert_unit)
                    measure_cert_unit = "psig"
                if measure_cert_unit == "MPa":
                    nominal = nominal * 1000
                    nominal_unit = "kPa"
                    measure_cert = measure_cert * 1000
                    measure_cert_unit = "kPa"
                    
            found = False
            for range_info in accreditation["measurement_uncertainty"]:
                if range_info["unit"] == nominal_unit and is_measure_cert_valid_float:
                    found = True
  
                    if range_info["range"][0] <= nominal <= range_info["range"][1]:
                        # print(colored(f"{range_info['range'][0]} {nominal_unit} <= {nominal} {nominal_unit} <= {range_info['range'][1]} {nominal_unit}", "green"))

                        print(colored(f"Certainty: {measure_cert} {measure_cert_unit}", "yellow"))
                        try:
                            variable_uncertainty = range_info["variable_uncertainty"]
                            variable_uncertainty_unit = range_info["variable_uncertainty_unit"]
                            if variable_uncertainty_unit == "%":
                                variable_uncertainty = float(nominal) * float(variable_uncertainty)
                                
                            elif variable_uncertainty_unit == "μinH2O/inH2O":
                                variable_uncertainty = float(variable_uncertainty) * float(nominal)
                                print(colored(f"Variable Uncertainty: {variable_uncertainty} {nominal_unit}", "yellow"))
                            else:
                                print(colored(f"Unknown variable uncertainty unit: {variable_uncertainty_unit}", "red"))
                        except Exception as e:
                            # print(e)
                            print(range_info["range"])
                            variable_uncertainty = 0
                            
                        fixed_uncertainty = range_info["fixed_uncertainty"]
                        required_uncertainty = fixed_uncertainty + variable_uncertainty
                        print(colored(f"Required Uncertainty: {required_uncertainty} {nominal_unit}", "yellow"))
                        if measure_cert <= required_uncertainty*0.99:
                            print(colored(f"Failed: {measure_cert} {measure_cert_unit} <= {required_uncertainty} {nominal_unit}", "red"))
                            result = {
                                "CertNo": certno,
                                "Nominal": nominal,
                                "Required Uncertainty": required_uncertainty,
                                "Measured Uncertainty": measure_cert,
                                "Result": "Failed"
                            }
                            results.append(result)
                        break
                    
            if not found:
                print(colored(f"Could not find range for === {measure_cert}{measure_cert_unit}", "red"))

save_json(results, 'pressure_results', 'Final_Pressure_Results')