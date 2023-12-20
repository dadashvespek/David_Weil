from json_processing import save_json, convert_to_grams
import json
import glob
import os
import math
from termcolor import colored
from directions import split_directions
from fileprocessing import lower_percent_of_max_ecce, lower_percent_of_max_rep, upper_percent_of_max_ecce, upper_percent_of_max_rep, exclusion_list
from googlesearch import search
os.makedirs('Final_Results', exist_ok=True)
list_of_all_json = glob.glob(os.path.join('inputjson', '*.json'))
json_data_list=json.load(open(list_of_all_json[0], 'r', encoding='utf-8'))

dict_of_noms = {}
group_values = []
results = [] 

for i in json_data_list:
    model=i.get("Model", "Unknown ModelNo")
    manufacturer=i.get("Manufacturer", "Unknown Manufacturer")
    search_term = f"Linearity specification for {manufacturer} {model} scale"
    print(search_term)
    for result in search(search_term, num_results=3,advanced=True):
        print(result.description)