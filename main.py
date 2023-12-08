import re
from support import crop_list, json_template_for_details,json_template_for_weights, call_gpt,check_measurement_uncertainty_nested
from json_processing import extract_json_from_text, save_json, extract_and_convert_to_dict,save_or_append_text_with_json_id
import json
import PyPDF2
import glob
from openai import OpenAI
import os
OPENAI_KEY='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'
client = OpenAI(api_key=OPENAI_KEY)
list_of_all_pdfs_in_docs_folder = glob.glob(os.path.join('docs', '*.pdf'))
for pdf in list_of_all_pdfs_in_docs_folder:
    with open(pdf, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        all_pages_text = []
        for page in pdf_reader.pages:
            all_pages_text.append(page.extract_text())

    def extract_and_convert_to_dict(json_str):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            return None
    start_marker = 'ID Inst'
    end_markers = ['REVISION COMMENT', 'SIGNATURES']


    gptresponse = call_gpt(client,all_pages_text[0], json_template_for_details)

    save_or_append_text_with_json_id(gptresponse.choices[0].message.content)
    gptjson = extract_and_convert_to_dict(gptresponse.choices[0].message.content)
    all_pages_text.remove(all_pages_text[0])
    if isinstance(gptjson, dict):
        jsonsavepath = os.path.join('Jsons', gptjson['ID_Inst'] + '.json')
    else:
        print("Error: GPT-3 did not return a JSON object")
        exit(1)
    if os.path.exists(jsonsavepath):
        gptjson = json.load(open(jsonsavepath))
    else:
        gptjson['Weights'] = []
        for page in all_pages_text:
            gptresponse2 = call_gpt(client,page.strip('\n'), json_template_for_weights)
            save_or_append_text_with_json_id(gptresponse2.choices[0].message.content)
            gptjson2 = extract_json_from_text(gptresponse2.choices[0].message.content)
            gptjson['Weights'].append(gptjson2)
        save_json(gptjson, gptjson['ID_Inst'],'Jsons')
    certjson = json.load(open('certjson.json',encoding='utf-8'))

    final_results = check_measurement_uncertainty_nested(gptjson, certjson)
    save_json(final_results, gptjson['ID_Inst'],'Final_Results')