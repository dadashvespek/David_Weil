import json
import os
def extract_json_from_text(text):
    # Searching for the JSON block within the text
    json_start = text.find('```json') + len('```json\n')
    json_end = text.find('```', json_start)
    json_string = text[json_start:json_end].strip()

    # Parsing the JSON string
    try:
        json_data = json.loads(json_string)
    except json.JSONDecodeError:
        return "Invalid JSON format."

    return json_data


import re
def extract_and_convert_to_dict(input_string):
    # Extract the JSON-like string using regular expression
    match = re.search(r"```json\n\{(.+?)\}\n```", input_string, re.DOTALL)
    if not match:
        return "No JSON-like content found"

    json_like_string = match.group(0)

    # Replace single quotes with double quotes and remove the markdown code block syntax
    valid_json_string = json_like_string.replace("'", '"').replace("```json\n", "").replace("\n```", "")

    # Convert the string to a dictionary
    try:
        data_dict = json.loads(valid_json_string)
    except json.JSONDecodeError:
        return "Invalid JSON format"

    return data_dict

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


def convert_to_json(input_string):
    # Remove the ```json and ``` markers
    clean_string = input_string.replace("```json\n", "").replace("\n```", "")

    # Replace single quotes with double quotes
    json_compatible_string = clean_string.replace("'", '"')

    # Convert the string to a Python dictionary
    dictionary = json.loads(json_compatible_string)

    # Return the dictionary as a JSON formatted string
    return json.dumps(dictionary, indent=4)

# Example usage

def save_or_append_text_with_json_id(text):
    try:extracted_json = convert_to_json(text)
    except:extracted_json = extract_json_from_text(text)

    # Parse the JSON to get the 'ID_Inst' value
    json_data = json.loads(extracted_json)
    if isinstance(json_data, list):
        json_data = json_data[0]
    file_name = json_data.get('ID_Inst', 'default_filename') + '.txt'

    # Create the folder if it doesn't exist
    output_folder = 'gptoutputtexts'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # File path
    file_path = os.path.join(output_folder, file_name)

    # Check if the file exists and write or append accordingly
    if os.path.exists(file_path):
        with open(file_path, 'a') as file:
            file.write('\n----\n')  # Separator
            file.write(text)
    else:

        with open(file_path, 'w') as file:
            file.write(text)

    return f"Text processed for file {file_name} in folder {output_folder}"
