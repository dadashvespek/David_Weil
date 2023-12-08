def crop_list(data_list, start_marker, end_markers):
    try:
        start_index = data_list.index(start_marker)
    except ValueError:
        return []
    end_index = len(data_list) 

    for marker in end_markers:
        if marker in data_list:
            end_index = min(end_index, data_list.index(marker))

    # Crop the list from start_index to end_index
    cropped_list = data_list[start_index:end_index]

    return cropped_list

def call_gpt(client,section_text=None, json_template=None, note=None, rules=None):
    # Base prompt
    prompt_base = "Fill out the JSON based on the information:"
    if section_text is not None:
        prompt_base += f"\n`{section_text}`\n"
    if json_template is not None:
        prompt_base += f"""Please provide the following JSON by extracting only necessary information from the text above:\n```json\n{json_template}`\n"```"""
    if note is not None:
        prompt_base += f"Note: {note}\n"
    if rules:
        prompt_base += "\nRules:\n"
        for rule in rules:
            prompt_base += f"- {rule}\n"
    # Here, you would call the GPT API with the constructed prompt
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a text processor"},
            {"role": "user", "content": prompt_base}
        ]
    )

    return response

json_template_for_details={     "ID_Inst": "<numeric_id>",     "Description": "<text_description>",     "Cal_Date": "<date_in_format_mm/dd/yyyy>",     "Due_Date": "<date_in_format_mm/dd/yyyy>",     "Calibrated_by": "<person_name>",     "Calibrate_Date": "<date_in_format_mm/dd/yyyy>",     "Quality_Approval_by": "<person_name>",     "QA_Date": "<date_in_format_mm/dd/yyyy>", } 

json_template_for_weights="""[{"category": "<string indicating the measurement category, e.g., 'Weight - Sensitivity'>","measurements": [{"units": "<string indicating the measurement units, e.g., 'g'>","max_error_tolerance": "<float indicating the maximum error tolerance, e.g., 0.000007>","nominal": "<float indicating the nominal value, e.g., 10.0000086>","low_limit": "<float indicating the low limit value, e.g., 9.999995>","high_limit": "<float indicating the high limit value, e.g., 10.000023>","as_found": "<float indicating the as found value, e.g., 10.000012>","meas_uncert": "<string indicating the measurement uncertainty, e.g., '0.000015' or 'n/a' if not applicable>","TUR": "<string indicating the Test Uncertainty Ratio, e.g., '0.5:1' or 'n/a' if not applicable>"}// ... Additional measurement objects for the same category]}// ... Additional category objects]"""

from tqdm import tqdm
from termcolor import colored

def check_measurement_uncertainty_nested(json_data, certification):
    results = []
    weights = json_data.get("Weights", [])

    for weight_list in tqdm(weights, desc="Processing weights", colour='blue'):
        for weight in weight_list:
            # Check if weight is a dictionary
            if not isinstance(weight, dict):
                continue

            # Now safe to use .get() method
            category = weight.get("category", "Unknown Category")
            measurements = weight.get("measurements", [])
            for measurement in measurements:
                nominal = measurement.get("nominal")
                meas_uncert_str = measurement.get("meas_uncert")
                # handle 'n/a' measurement uncertainty
                try:
                    meas_uncert = float(meas_uncert_str)
                except: mass_uncert = 'n/a'
                if meas_uncert_str in ["n/a", "N/A", '**','**\nn/a',"''",''] or meas_uncert_str is None:
                    result = {
                        "category": category,
                        "nominal": nominal,
                        "measured_uncertainty": "n/a",
                        "required_uncertainty": "n/a",
                        "passed": "Not Applicable"
                    }
                    tqdm.write(colored("[Not Applicable] ", "yellow") + f"Category: {category}, Nominal: {nominal}, Measured Uncertainty: n/a")
                    results.append(result)
                    continue

                meas_uncert = float(meas_uncert_str)
                for range_info in certification["measurement_uncertainty"]:
                    nominal_value = float(nominal)
                    if range_info["range"][0] <= nominal_value <= range_info["range"][1]:
                        total_uncertainty = range_info["fixed_uncertainty"] + \
                                            range_info["variable_uncertainty"] * nominal_value
                        total_uncertainty /= 1e6  # µg to g
                        passed = meas_uncert >= total_uncertainty
                        status = "Passed" if passed else "Failed"
                        bar_color = "green" if passed else "red"
                        result = {
                            "category": category,
                            "nominal": nominal_value,
                            "measured_uncertainty": meas_uncert,
                            "required_uncertainty": total_uncertainty,
                            "passed": passed
                        }
                        tqdm.write(colored(f"[{status}] ", bar_color) + f"Category: {category}, Nominal: {nominal_value}, Measured Uncertainty: {meas_uncert}, Required Uncertainty: {total_uncertainty}")
                        results.append(result)
                        break
    return results