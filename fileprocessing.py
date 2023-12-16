import json

# Load the configuration
with open('config.json', 'r') as f:
    config = json.load(f)
exclusion_list = config["exclusion_list"]
lower_percent_of_max_rep = config["lower_percent_of_max_rep"]
upper_percent_of_max_rep = config["upper_percent_of_max_rep"]
lower_percent_of_max_ecce = config["lower_percent_of_max_ecce"]
upper_percent_of_max_ecce = config["upper_percent_of_max_ecce"]

(exclusion_list, lower_percent_of_max_rep, upper_percent_of_max_rep, lower_percent_of_max_ecce, upper_percent_of_max_ecce)