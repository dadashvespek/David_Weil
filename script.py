# script.py

import argparse
import os
import re
import json
import traceback
import sys
import subprocess
from collections import defaultdict
from datetime import datetime
from data_retriever import retrieve_data
from google_sheets_handler import send_results_to_sheets
from pressure_cert_processor import retrieve_pressure_data, process_pressure_certificates

# Redirect stdout to a file
sys.stdout = open('script_output.txt', 'w')

def read_schedule_config():
    """Read the schedule configuration from JSON file."""
    try:
        with open('schedule_config.json', 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Configuration file 'schedule_config.json' not found. Using default values.")
        return {"frequency": "daily", "times": ["06:00", "18:00"]}
    except json.JSONDecodeError:
        print("Error reading 'schedule_config.json'. Ensure it is properly formatted.")
        return {"frequency": "daily", "times": ["06:00", "18:00"]}

def create_task_scheduler():
    """Automates creating a Windows Task Scheduler task to run the script based on JSON configuration."""
    config = read_schedule_config()
    frequency = config.get("frequency", "daily")
    times = config.get("times", ["06:00", "18:00"])

    script_path = os.path.abspath(__file__)
    try:
        # Prepare PowerShell command for task creation
        task_name = "RunScriptBasedOnConfig"
        action = f'New-ScheduledTaskAction -Execute "python" -Argument "{script_path}"'
        
        triggers = []
        for time in times:
            hour, minute = time.split(":")
            if frequency == "daily":
                trigger = f'New-ScheduledTaskTrigger -Daily -At {hour}:{minute}AM'
            elif frequency == "weekly":
                trigger = f'New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At {hour}:{minute}AM'
            else:
                print(f"Unsupported frequency: {frequency}. Defaulting to daily.")
                trigger = f'New-ScheduledTaskTrigger -Daily -At {hour}:{minute}AM'
            triggers.append(trigger)

        # Construct the PowerShell command
        trigger_command = ", ".join(triggers)
        command = f"""
        $Action = {action}
        $Trigger = @({trigger_command})
        Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName "{task_name}" -Description "Run the Python script based on schedule config" -User "{os.getlogin()}"
        """
        
        # Run the PowerShell command to create the scheduled task
        subprocess.run(["powershell", "-Command", command], check=True)
        print(f"Task Scheduler job created successfully based on the configuration: {frequency} at {times}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create task scheduler job: {e}")


def parse_numeric_value(value):
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = re.sub(r'[^\d.-]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def additional_checks_ambient_temp_and_humidity(data):
    errors = []
    # Apply span checks only for specific equipment types and calibration location
    valid_equipment_types = ["thermohygrometer", "datalogger", "temperature and humidity meter"]

    # Only proceed if the certificate matches the criteria
    if (
        data.get("CalLocation", "").lower() == "on-site calibration" and
        data.get("EquipmentType", "").lower() in valid_equipment_types
    ):
        # Check if CalibrationStatus is "Limited"
        if data.get("CalibrationStatus", "").lower() != "limited":
            errors.append("Calibration status must be 'Limited' for On-Site Calibration.")

        # Span checks for humidity and temperature
        for datasheet in data.get("Datasheet", []):
            group_name = datasheet.get("Group", "").lower()
            measurements = datasheet.get("Measurements", [])

            # Perform span check only if it's related to humidity or temperature
            if "humedad relativa" in group_name or "humidity" in group_name:
                nominal_values = [
                    parse_numeric_value(m.get("Nominal"))
                    for m in measurements
                    if parse_numeric_value(m.get("Nominal")) is not None
                ]
                if nominal_values:
                    max_nominal = max(nominal_values)
                    min_nominal = min(nominal_values)
                    print(f"Humidity Group - Max Nominal: {max_nominal}, Min Nominal: {min_nominal}, Certificate: {data.get('CertNo')}")
                    if max_nominal - min_nominal > 10:
                        errors.append(f"Humidity span exceeds 10 %RH (Max: {max_nominal}, Min: {min_nominal})")

            if "temperatura" in group_name or "temperature" in group_name:
                nominal_values = [
                    parse_numeric_value(m.get("Nominal"))
                    for m in measurements
                    if parse_numeric_value(m.get("Nominal")) is not None
                ]
                if nominal_values:
                    max_nominal = max(nominal_values)
                    min_nominal = min(nominal_values)
                    print(f"Temperature Group - Max Nominal: {max_nominal}, Min Nominal: {min_nominal}, Certificate: {data.get('CertNo')}")
                    if max_nominal - min_nominal > 5:
                        errors.append(f"Temperature span exceeds 5 °C (Max: {max_nominal}, Min: {min_nominal})")

    return errors


def check_environmental_conditions(data):
    temp = data.get("EnvironmentalTemperature", "")
    humidity = data.get("EnvironmentalRelativeHumidity", "")
    
    # Remove only the degree symbol
    temp = temp.replace("\u00b0", "").strip()
    
    # Check if temperature is in Celsius or Fahrenheit
    if temp.endswith('C'):
        temp_c = parse_numeric_value(temp[:-1])
        temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
    elif temp.endswith('F'):
        temp_f = parse_numeric_value(temp[:-1])
        temp_c = (temp_f - 32) * 5/9 if temp_f is not None else None
    else:
        # If no unit is specified, try to parse as is
        temp_f = parse_numeric_value(temp)
        temp_c = (temp_f - 32) * 5/9 if temp_f is not None else None

    humidity_pct = parse_numeric_value(humidity.replace("%RH", "").strip())
    
    temp_check = (60 <= temp_f <= 100) if temp_f is not None else (15 <= temp_c <= 40 if temp_c is not None else False)
    humidity_check = 30 <= humidity_pct <= 80 if humidity_pct is not None else False
    
    return temp_check and humidity_check

def check_front_page(data):
    required_fields = [
        "CertNo", "CustomerCode", "EquipmentType", "AssetDescription",
        "Manufacturer", "Model", "OperatingRange", "EquipmentLocation"
    ]

    # Retrieve and normalize UsedPipetteModule and AttachmentTypesUsed values
    use_pipette = data.get("UsedPipetteModule", False)
    attachments_used = data.get("AttachmentTypesUsed", [])

    # Determine if this certificate should skip accreditation checks
    is_from_hasattachment = not use_pipette and bool(attachments_used)

    # Debugging: Print out values we care about
    print(f"Certificate: {data.get('CertNo')}, UsedPipetteModule: {use_pipette}, AttachmentsUsed: {attachments_used}, IsFromHasAttachment: {is_from_hasattachment}")

    # Add AccreditationInfo only if the certificate is accredited and not from HasAttachment or Pipette Module
    is_accredited = data.get("IsAccredited", False)
    if is_accredited and not is_from_hasattachment:
        print(f"Adding accreditation fields for certificate: {data.get('CertNo')}")
        required_fields.extend(["Procedures", "Standards", "AccreditationInfo"])

    # Check for missing fields
    missing_fields = []
    for field in required_fields:
        value = data.get(field)
        if value is None or value == "null" or (isinstance(value, str) and not value.strip()):
            missing_fields.append(field)
        elif isinstance(value, list) and not value:
            missing_fields.append(field)

    return len(missing_fields) == 0, missing_fields

def check_accreditation(data):
    is_accredited = data.get("IsAccredited", False)
    use_pipette = data.get("UsedPipetteModule", False)
    attachments_used = data.get("AttachmentTypesUsed", [])

    # Skip accreditation check for pipette or attachment certificates
    if not is_accredited or use_pipette or bool(attachments_used):
        return True

    # Check accreditation only if it's not a pipette and has no attachments
    for group in data.get("Datasheet", []):
        for measurement in group.get("Measurements", []):
            meas_uncert = measurement.get("MeasUncert")
            if meas_uncert not in [None, "", "**"]:
                uncert_value = parse_numeric_value(meas_uncert)
                if uncert_value is not None:
                    return True

    # Check for alternative conditions
    if "External Certificate" in attachments_used:
        return True
    if data.get("HasModule/Wizard"):
        return True

    return False

def check_customer_requirements_for_tur(data):
    customer_requirements = data.get("CustomerRequirements", [])
    return any("#CalibrationReqs: TUR Requerido: 4:1" in req for req in customer_requirements)

def check_tur(data):
    if not check_customer_requirements_for_tur(data):
        return True, []  # TUR check is not required, so it passes by default

    low_tur_values = []
    for group in data.get("Datasheet", []):
        for measurement in group.get("Measurements", []):
            tur = measurement.get("TUR", "")
            if tur and ":" in tur:
                ratio_str, _ = tur.split(":")
                ratio = parse_numeric_value(ratio_str)
                if ratio is not None and ratio < 4:
                    low_tur_values.append(tur)
    return len(low_tur_values) == 0, low_tur_values

def check_template_status(data):
    return data.get("TemplateUsedStatus") == "Not Edited"

def check_certificate(cert_data):
    print(f"\nChecking certificate: {cert_data.get('CertNo', 'Unknown')}")
    print(f"Equipment Type: {cert_data.get('EquipmentType', 'Unknown')}")
    cert_no = cert_data.get('CertNo', 'Unknown')
    cal_date = cert_data.get('CalDate', '')
    print(f"Checking certificate: {cert_no} with CalDate: {cal_date}")

    # Ensure CalibrationResult is "Limited" for On-Site Calibration
    if cert_data.get("CalLocation", "").lower() == "on-site calibration" and cert_data.get("CalibrationResult", "").lower() != "limited":
        cert_data["CalibrationResult"] = "Limited"

    # Sort Datasheet by CalDate for all certificates
    try:
        cert_data['Datasheet'] = sorted(cert_data['Datasheet'], key=lambda d: datetime.strptime(cert_data.get('CalDate', 'Jan/01/1900'), '%b/%d/%Y'))
    except ValueError:
        print("Invalid CalDate format for sorting")

    # Perform additional checks for ambient temperature and humidity
    additional_errors = additional_checks_ambient_temp_and_humidity(cert_data)
    if additional_errors:
        print(f"Additional checks failed: {additional_errors}")

    # Determine if this certificate uses a template
    is_template_cert = cert_data.get("TemplateUsed") is not None

    env_conditions = check_environmental_conditions(cert_data)
    print(f"Environmental conditions check: {env_conditions}")

    front_page_check, front_page_missing = check_front_page(cert_data)
    print(f"Front page check: {front_page_check}, Missing: {front_page_missing}")

    accreditation = check_accreditation(cert_data)
    print(f"Accreditation check: {accreditation}")

    tur_check, tur_values = check_tur(cert_data)
    print(f"TUR check: {tur_check}, Values: {tur_values}")

    template_status = True
    if is_template_cert:
        template_status = check_template_status(cert_data)
        print(f"Template status check: {template_status}")

    # If any of the required fields are missing, mark the certificate as failed
    if not front_page_check:
        print(f"Certificate {cert_no} has missing front page fields: {front_page_missing}")

    results = {
        "environmental_conditions": env_conditions,
        "front_page_complete": (front_page_check, front_page_missing),
        "accreditation": accreditation,
        "tur": (tur_check, tur_values),
        "template_status": template_status,
        "additional_checks": (len(additional_errors) == 0, additional_errors)
    }

    formatted_errors = format_errors(results, cert_data, is_template_cert)
    return results, formatted_errors

def local_retrieve_data():
    retrieve_data()
    all_data = []
    input_dir = './inputjson'
    file_patterns = [
        'data_response_IR Temp.json',
        'data_response_Ambient Temp_Hum.json',
        'data_response_scales.json',
        'data_response_UseTemplate_True.json',
        'data_response_UsePipetteModule_True.json',
        'data_response_HasAttachments_True.json'
    ]

    for file_name in file_patterns:
        file_path = os.path.join(input_dir, file_name)
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                if isinstance(data, list):
                    all_data.extend(data)
                    print(f"Loaded {len(data)} certificates from {file_name}")
                else:
                    all_data.append(data)
                    print(f"Loaded 1 certificate from {file_name}")
        except FileNotFoundError:
            print(f"Warning: File '{file_path}' not found.")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in file '{file_path}'.")

    print(f"Total certificates loaded: {len(all_data)}")
    return all_data

def format_errors(result, cert_data, is_template_cert):
    formatted_errors = {
        "FrontPageErrors": [],
        "DatasheetErrors": [],
        "TemplateStatusError": None
    }

    print(f"\nFormatting errors for certificate: {cert_data.get('CertNo', 'Unknown')}")
    print(f"Result: {result}")
    print(f"Is Template Cert: {is_template_cert}")

    # Process front page errors
    if not result["front_page_complete"][0]:
        formatted_errors["FrontPageErrors"].extend(result["front_page_complete"][1])

    # Process accreditation error
    if not result["accreditation"]:
        formatted_errors["FrontPageErrors"].append("AccreditationInfo")

    # Process TUR errors
    if not result["tur"][0]:
        for group in cert_data.get("Datasheet", []):
            group_errors = []
            for measurement in group.get("Measurements", []):
                tur = measurement.get("TUR", "")
                row_id = measurement.get("RowId", "Unknown RowId")
                if tur and ":" in tur:
                    ratio_str, _ = tur.split(":")
                    ratio = parse_numeric_value(ratio_str)
                    if ratio is not None and ratio < 4:
                        group_errors.append({
                            "RowId": row_id,
                            "Error": f"Low TUR: {tur} in certificate '{cert_data.get('CertNo', 'Unknown CertNo')}'"
                        })
            if group_errors:
                formatted_errors["DatasheetErrors"].append({
                    "Group": group["Group"],
                    "Errors": group_errors
                })

    # Process environmental conditions error
    if not result["environmental_conditions"]:
        formatted_errors["FrontPageErrors"].append("EnvironmentalConditions")

    # Process template status error
    if is_template_cert and not result["template_status"]:
        formatted_errors["TemplateStatusError"] = "Template has been edited"

    # Add additional checks errors
    if not result["additional_checks"][0]:
        formatted_errors["FrontPageErrors"].extend(result["additional_checks"][1])

    print(f"Formatted Errors: {formatted_errors}")

    return formatted_errors

def main(all_data):
    passed_certs_main = defaultdict(list)
    failed_certs_main = defaultdict(list)
    draft_certs_main = defaultdict(list)
    skipped_certs_main = defaultdict(list)

    total_certificates = 0

    for data_set in all_data:
        if isinstance(data_set, list):
            certs = data_set
        elif isinstance(data_set, dict):
            certs = [data_set]
        else:
            print(f"Skipping invalid data set: {data_set}")
            continue

        total_certificates += len(certs)
        print(f"\nProcessing {len(certs)} certificates")

        for cert in certs:
            try:
                # Retrieve and normalize calibration status
                calibration_status = cert.get("CalibrationStatus", "").strip().lower()

                cert_no = cert.get("CertNo", "Unknown")
                cal_date = cert.get("CalDate", "")
                equipment_type = cert.get("EquipmentType", "Unknown")
                customer_code = cert.get("CustomerCode", "Unknown")

                # Handle draft certificates
                if calibration_status == "draft":
                    draft_certs_main[equipment_type].append({
                        "CertNo": cert_no,
                        "CalDate": cal_date,
                        "CustomerCode": customer_code,
                        "CalibrationStatus": calibration_status
                    })
                    print(f"Certificate {cert_no} is in 'Draft' status and added to draft certificates.")
                    continue  # Skip further processing for this certificate

                # Handle ready to approve certificates
                elif calibration_status == "ready to approve":
                    # Perform front-page checks even for scales and balances certificates
                    front_page_check, front_page_missing = check_front_page(cert)
                    if not front_page_check:
                        failed_certs_main[equipment_type].append({
                            "CertNo": cert_no,
                            "CalDate": cal_date,
                            "CustomerCode": customer_code,
                            "Errors": {"FrontPageErrors": front_page_missing}
                        })
                        print(f"Certificate {cert_no} failed front-page checks due to missing fields: {front_page_missing}")
                        continue  # Skip further processing if front-page checks fail

                    # If it's a scales and balances certificate, delegate to pressure certificate processing
                    if equipment_type == "Scales & Balances":
                        print(f"Passing scales and balances certificate {cert_no} to pressure processing.")
                        # Handled in process_pressure_certificates()
                        continue

                    # Proceed with error checking for other types
                    result, formatted_errors = check_certificate(cert)

                    # Check if all results are True or (True, [])
                    if all(value if isinstance(value, bool) else value[0] for value in result.values()):
                        passed_certs_main[equipment_type].append({
                            "CertNo": cert_no,
                            "CalDate": cal_date,
                            "CustomerCode": customer_code
                        })
                        print(f"Certificate {cert_no} passed all checks")
                    else:
                        failed_certs_main[equipment_type].append({
                            "CertNo": cert_no,
                            "CalDate": cal_date,
                            "CustomerCode": customer_code,
                            "Errors": formatted_errors
                        })
                        print(f"Certificate {cert_no} failed checks: {formatted_errors}")


                # Handle other statuses explicitly
                else:
                    print(f"Certificate {cert_no} has status '{calibration_status}' and is being skipped.")
                    skipped_certs_main[equipment_type].append(cert)

            except Exception as e:
                # Exception handling
                error_message = f"{str(e)}\n{traceback.format_exc()}"
                failed_certs_main[equipment_type].append({
                    "CertNo": cert_no,
                    "CalDate": cal_date,
                    "CustomerCode": customer_code,
                    "Errors": {"UnexpectedError": [error_message]}
                })
                print(f"Unexpected error processing certificate {cert_no}: {error_message}")

    # Process pressure (scales and balances) certificates
    pressure_data = retrieve_pressure_data()
    if pressure_data is not None:
        passed_certs_pressure, failed_certs_pressure = process_pressure_certificates()
    else:
        print("Skipping pressure certificate processing due to retrieval error.")
        passed_certs_pressure = defaultdict(list)
        failed_certs_pressure = defaultdict(list)

    # Merge only passed pressure certificates into main passed certificates
    for eq_type, certs in passed_certs_pressure.items():
        passed_certs_main[eq_type].extend(certs)

    # Merge failed pressure certificates into main failed certificates
    for eq_type, certs in failed_certs_pressure.items():
        failed_certs_main[eq_type].extend(certs)

    # Send results to Google Sheets
    user_email = "your_email@example.com"  # Replace with your actual email
    sheet_url = send_results_to_sheets(
        passed_certs_main, failed_certs_main, draft_certs_main,
        failed_certs_pressure, user_email
    )

    print(f"You can access the Google Sheet at: {sheet_url}")

    # Return all categories for further processing
    return passed_certs_main, failed_certs_main, draft_certs_main, skipped_certs_main, passed_certs_pressure, failed_certs_pressure, total_certificates

if __name__ == "__main__":
    # Argument parser to decide whether to schedule or run normally
    parser = argparse.ArgumentParser(description="Process certificates or set up a scheduler for this script.")
    parser.add_argument("--schedule", action="store_true", help="Set up Windows Task Scheduler to run this script twice a day.")
    args = parser.parse_args()

    if args.schedule:
        # If the --schedule argument is passed, create the scheduler
        if not os.path.exists("task_scheduled.txt"):
            create_task_scheduler()
            with open("task_scheduled.txt", "w") as f:
                f.write("Task scheduled successfully.")
            print("Task has been scheduled successfully.")
        else:
            print("Task has already been scheduled.")
    else:
        # Redirect stdout to a file, process, and then reset stdout
        with open('script_output.txt', 'w') as f:
            sys.stdout = f

            # Retrieve data from local files
            all_data = local_retrieve_data()

            # Process the JSON data
            passed_certs_main, failed_certs_main, draft_certs_main, skipped_certs_main, passed_certs_pressure, failed_certs_pressure, total_certificates = main(all_data)

        # Reset stdout to default
        sys.stdout = sys.__stdout__

        # Write summary
        print("\nSummary:")
        total_passed = sum(len(certs) for certs in passed_certs_main.values()) + sum(len(certs) for certs in passed_certs_pressure.values())
        total_failed = sum(len(certs) for certs in failed_certs_main.values()) + sum(len(certs) for certs in failed_certs_pressure.values())
        total_drafts = sum(len(certs) for certs in draft_certs_main.values())
        total_skipped = sum(len(certs) for certs in skipped_certs_main.values())
        print(f"Total certificates processed: {total_certificates}")
        print(f"Passed certificates: {total_passed}")
        print(f"Failed certificates: {total_failed}")
        print(f"Draft certificates: {total_drafts}")
        print(f"Skipped certificates: {total_skipped}")

        # Write results to files
        with open('passed_certificates.txt', 'w') as f:
            f.write("Certificates that passed all checks:\n")
            if not any(passed_certs_main.values()) and not any(passed_certs_pressure.values()):
                f.write("\nNo certificates passed all checks.\n")
            else:
                # Write main passed certificates
                for equipment_type, certs in passed_certs_main.items():
                    if certs:
                        f.write(f"\nEquipment Type: {equipment_type}\n")
                        for cert in certs:
                            f.write(f"{cert}\n")
                # Write pressure passed certificates
                for equipment_type, certs in passed_certs_pressure.items():
                    if certs:
                        f.write(f"\nEquipment Type: {equipment_type}\n")
                        for cert in certs:
                            f.write(f"{cert}\n")

        with open('failed_certificates.txt', 'w') as f:
            f.write("Certificates that failed one or more checks:\n")
            if not any(failed_certs_main.values()) and not any(failed_certs_pressure.values()):
                f.write("\nNo certificates failed any checks.\n")
            else:
                # Write main failed certificates
                for equipment_type, certs in failed_certs_main.items():
                    if certs:
                        f.write(f"\nEquipment Type: {equipment_type}\n")
                        for cert in certs:
                            f.write(f"Certificate: {cert['CertNo']}\n")
                            errors = cert['Errors']
                            if errors.get("FrontPageErrors"):
                                f.write("Front Page Errors: " + ", ".join(errors["FrontPageErrors"]) + "\n")
                            if errors.get("DatasheetErrors"):
                                f.write("Datasheet Errors:\n")
                                for group in errors["DatasheetErrors"]:
                                    f.write(f"  Group: {group['Group']}\n")
                                    for error in group['Errors']:
                                        f.write(f"    Row {error['RowId']}: {error['Error']}\n")
                            f.write("\n")
                # Write pressure failed certificates
                for equipment_type, certs in failed_certs_pressure.items():
                    if certs:
                        f.write(f"\nEquipment Type: {equipment_type}\n")
                        for cert in certs:
                            f.write(f"Certificate: {cert['CertNo']}\n")
                            errors = cert['Errors']
                            if errors.get("DatasheetErrors"):
                                f.write("Datasheet Errors:\n")
                                for group in errors["DatasheetErrors"]:
                                    f.write(f"  Group: {group['Group']}\n")
                                    for error in group['Errors']:
                                        f.write(f"    Row {error['RowId']}: {error['Error']}\n")
                            f.write("\n")

        print(f"Results have been written to 'passed_certificates.txt' and 'failed_certificates.txt'")