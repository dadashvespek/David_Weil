from json_processing import save_json, convert_to_grams
import json
import glob
import os
import math
from termcolor import colored
from directions import split_directions
from fileprocessing import lower_percent_of_max_ecce, lower_percent_of_max_rep, upper_percent_of_max_ecce, upper_percent_of_max_rep, exclusion_list
from data_retriever import retrieve_data
from report_generator import generate_pdf

os.makedirs('Final_Results', exist_ok=True)
def check_measurement_uncertainty_nested(json_data_list, certification):
    results_by_certno = {} 
    nominal_std=0
    unitofnominal='g'
    passed_certificates = set()
    for json_data in json_data_list:
        dict_of_noms = {}
        group_values = []
        results = [] 
        datasheets = json_data.get("Datasheet", [])
        CertNo = json_data.get("CertNo", "Unknown CertNo")
        # if 'C343701' not in CertNo:
        #     continue

        asset_description = json_data.get("AssetDescription", "Unknown AssetDescription")
        excluded=any(keyword in asset_description.lower() for keyword in exclusion_list)
        
        print(colored(f"CertNo: {CertNo}", "blue"))
        
        std_passed = False
        for datasheet in datasheets:
            group = datasheet.get("Group", "Unknown Group")

            group_values.append(group)
            if 'std' in group.lower() or 'desviación' in group.lower():
                std_passed = True
            if group.split(' ')[-1].lower()=='weight' or group.split(' ')[-1].lower()=='peso' or group.lower=='weight' or 'rep' in group.lower():
                measure = datasheet.get("Measurements", [])
                max_nominal_std = None
                for i in measure:
                    nom = i.get("Nominal")
                    unitofmaxnom = i.get("Units")
                    nom = float(convert_to_grams(nom, unitofmaxnom))
                    if max_nominal_std is None:
                        max_nominal_std = nom
                    elif nom > max_nominal_std:
                        max_nominal_std = nom
                nominal_std = max_nominal_std
                unitofnominal = unitofmaxnom
                dict_of_noms['Group - Repeatability'] = max_nominal_std
            not_present = []
            for direction, parts in split_directions.items():
                found = False
                for part in parts:
                    for element in group_values:
                        if part.lower() in element.lower():
                            # print(f"Direction '{direction}' found in group value element: {element}")
                            
                            found = True
                            break  
                    if found:
                        break  
                if not found:
                    not_present.append(direction)


        if not_present != [] and not excluded:
            
            print(colored(f"Directions not present: {not_present}", "blue"))
            results.append({"Directions not present": not_present})

        if not std_passed and not excluded:
            result ={
                "STD_Present": False,
            }
            print(colored(f"[Failed] No std group found", "red"))

            results.append(result)

        
        total_measurements_up_dw = []
        for datasheet in datasheets:
            group = datasheet.get("Group", "Unknown Group")
            
            measurements = datasheet.get("Measurements", [])
            if any(keyword in group.lower() for keyword in ['up', 'ascendente','down','dw','dn','descendente']):
                total_measurements_up_dw.append(len(measurements))
                max_nominal = None
                for i in measurements:
                    nom = i.get("Nominal")
                    unitofmaxnom = i.get("Units")
                    nom = float(convert_to_grams(nom, unitofmaxnom))
                    if max_nominal is None:
                        max_nominal = nom
                        
                    elif nom > max_nominal:
                        max_nominal = nom
                    
                print(colored(f"Max Nominal: {max_nominal}g", "yellow"))
                nominal_std = float(nominal_std)
            
                nominal_std_converted = convert_to_grams(nominal_std, unitofnominal)
                print(colored(f"Nominal: {nominal_std_converted}g", "yellow"))
                #add to dict of noms
                if any(keyword in group.lower() for keyword in ['up', 'ascendente','down','dw','dn','descendente','descendente','descendete']):
                    dict_of_noms['Weight - Linearity'] = max_nominal

            elif group.split(' ')[-1].lower()=='weight' or group.split(' ')[-1].lower()=='peso' or group.lower=='weight' or 'rep' in group.lower():
                continue
            else:
                max_nominal = None
                for i in measurements:
                    nom = i.get("Nominal")
                    unitofmaxnom = i.get("Units")
                    nom = float(convert_to_grams(nom, unitofmaxnom))
                    if max_nominal is None:
                        max_nominal = nom
                        
                    elif nom > max_nominal:
                        max_nominal = nom
                dict_of_noms[group] = max_nominal
            

       

            for measurement in measurements:
                nominal = measurement.get("Nominal")
                meas_uncert_str = measurement.get("MeasUncert")
                if meas_uncert_str in ["n/a", "N/A", '**', '**\nn/a', "''", ''] or meas_uncert_str is None:
                    continue

                meas_uncert = convert_to_grams(float(meas_uncert_str), measurement.get("MeasUnit"))

                if meas_uncert != 'n/a' and meas_uncert != 'N/A':
                    for range_info in certification["measurement_uncertainty"]:
                        if nominal != 'N/A':
                            nominal_value = float(nominal)
                            nominal_value = convert_to_grams(nominal_value, measurement.get("Units"))
                            test_nominal_value = nominal_value *0.99
                        else:
                            continue


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
                                    "error_message": f"Measured uncertainty {meas_uncert}g is not within required uncertainty {total_uncertainty}g"

                                }
                                
                                print(colored(f"[{status}] Group: {group}, Nominal: {nominal_value}g, Measured Uncertainty: {meas_uncert}g, Required Uncertainty: {total_uncertainty}g", color))
                                results.append(result)

        if results:
            results_by_certno[CertNo] = results
        else:
            print(colored(f"=========================================\n[Passed] All measurements are within the required uncertainty\n=========================================\n", "green"))
            passed_certificates.add(CertNo)


        max_linearity = dict_of_noms.get('Weight - Linearity', 0)
        if len(total_measurements_up_dw)>1:
            total_measures = sum(total_measurements_up_dw)
            if total_measures>= 9:
                # print(colored(f"[Passed] Number of measurements: {total_measures}", "green"))
                pass
            else:
                print(colored(f"[Failed] Number of measurements: {total_measures}", "red"))
                results.append({f"Number of measurements": total_measures, "Number of measurements 9 or more": False})

        for key, value in dict_of_noms.items():
            if key.split(' ')[-1].lower()=='weight' or key.split(' ')[-1].lower()=='peso' or key.lower=='weight' or 'rep' in key.lower() and not excluded:
                if not (lower_percent_of_max_rep * max_linearity <= value <= max_linearity * upper_percent_of_max_rep):
                    error_message = f"{key} with a maximum value of {value}g is not within {round(lower_percent_of_max_ecce*100,1)}% to {round(upper_percent_of_max_rep*100)}% of max linearity {max_linearity}g"
                    result = {
                        "group": key,
                        "nominal": f"{value}g",
                        "error_message": error_message,
                    }
                    print(colored(error_message, "red"))
                    if CertNo in results_by_certno:
                        results_by_certno[CertNo].append(result)
                    else:
                        results_by_certno[CertNo] = [result]
            if 'eccentricity' in key.lower() and not ( lower_percent_of_max_ecce * max_linearity <= value <= upper_percent_of_max_ecce * max_linearity) and not excluded:
                error_message = f"Error2: {key} value {value}g is not within {round(lower_percent_of_max_ecce*100,1)}% to {upper_percent_of_max_ecce*100}% of max linearity {max_linearity}g"
                result = {
                    "group": key,
                    "nominal": f"{value}g",
                    "error_message": error_message,
                }
                if value > 0:
                    print(colored(error_message, "red"))
                    if CertNo in results_by_certno:
                        results_by_certno[CertNo].append(result)
                    else:
                        results_by_certno[CertNo] = [result]

    

    return results_by_certno, passed_certificates


import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service

def send_email(pdf_path):
    service = get_gmail_service()

    # Create the email message
    message = MIMEMultipart()
    message['to'] = 'labsupport@phoenixcalibrationdr.com, quality@phoenixcalibrationdr.com'
    message['subject'] = 'Measurement Uncertainty Report'

    # Attach the PDF report
    with open(pdf_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype='pdf')
        attachment.add_header('Content-Disposition', 'attachment', filename='report.pdf')
        message.attach(attachment)

    # Send the email
    create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    send_message = (service.users().messages().send(userId="me", body=create_message).execute())
    print(F'sent message to {message["to"]} Message Id: {send_message["id"]}')

def main():
    # Load the certjson.json file
    with open('certjson.json', 'r', encoding='utf-8') as f:
        cert_data = json.load(f)

    # Retrieve the data from the data_retriever module
    data = retrieve_data()

    # Call the check_measurement_uncertainty_nested function with the retrieved data and cert_data
    # processed_data = check_measurement_uncertainty_nested(data, cert_data)
    processed_data, passed_certificates = check_measurement_uncertainty_nested(data, cert_data)

    # Generate the PDF report using the processed data
    # generate_pdf(processed_data)
    generate_pdf(processed_data, passed_certificates)
    # send_email('report.pdf')

if __name__ == "__main__":
    main()