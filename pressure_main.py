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
                measure_cert = float(measure_cert)
            except:
                continue
            measure_cert_unit = measure_cert_unit.split(" ")[0] 
            og_sign1 = measure_cert_unit
            og_sign2 = nominal_unit
            if measure_cert_unit != "psig":
                print(f"Before: {nominal}{nominal_unit} ")
                nominal = convert_to_psig(nominal, nominal_unit)
                nominal_unit = "psig"
                print(f"After: {nominal}{nominal_unit} ")
                measure_cert = convert_to_psig(measure_cert,measure_cert_unit)
                measure_cert_unit = 'psig'

            largest_required_uncertainty = 0
            found = False
            for range_info in accreditation["measurement_uncertainty"]:
                if range_info["range"][0] <= nominal <= range_info["range"][1]:
                    found = True
                    
                    try:
                        variable_uncertainty = range_info["variable_uncertainty"]
                        variable_uncertainty_unit = range_info["variable_uncertainty_unit"]
                        
                        if variable_uncertainty_unit == "%":
                            variable_uncertainty = nominal * (float(variable_uncertainty)/100)
                        elif variable_uncertainty_unit == "μpsig/psig":
                            variable_uncertainty = float(variable_uncertainty) * nominal
                            print(colored(f"Variable Uncertainty: {variable_uncertainty} {nominal_unit}", "yellow"))
                        else:
                            print(colored(f"Unknown variable uncertainty unit: {variable_uncertainty_unit}", "red"))
                    except Exception as e:
                        print(range_info["range"])
                        print("!!!!!!!!!!!!!!!")
                        variable_uncertainty = 0
                        print(required_uncertainty)
        

                    fixed_uncertainty = range_info["fixed_uncertainty"]
                    required_uncertainty = fixed_uncertainty + variable_uncertainty
                    print(colored(f"Required Uncertainty: {required_uncertainty} {nominal_unit}", "yellow"))
                    
                    if required_uncertainty > largest_required_uncertainty:
                        largest_required_uncertainty = required_uncertainty

            if found:
                if measure_cert <= largest_required_uncertainty * 0.99:
                    print(colored(f"Failed: {measure_cert} {measure_cert_unit} <= {largest_required_uncertainty} {nominal_unit}", "red"))
                    result = {
                        "CertNo": certno,
                        "Nominal": nominal,
                        "Required Uncertainty": largest_required_uncertainty,
                        "Measured Uncertainty": measure_cert,
                        "og sign":f"{og_sign1} and {og_sign2}",
                        "Result": "Failed"
                    }
                    results.append(result)
                else:
                    print(colored(f"Passed: {measure_cert} {measure_cert_unit} > {largest_required_uncertainty} {nominal_unit}", "green"))
                    # Add code here to append a pass result if needed
            else:
                print(colored(f"Could not find range for === {measure_cert}{measure_cert_unit}", "red"))

                
        if not found:
            print(colored(f"Could not find range for === {measure_cert}{measure_cert_unit}", "red"))

save_json(results, 'pressure_results', 'Final_Pressure_Results')