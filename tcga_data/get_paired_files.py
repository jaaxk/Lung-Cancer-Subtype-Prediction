import requests
import os
import json

## AFTER GETTING METADATA FILE OF CART:
# Cart should contain TSV files filtered for: RNA-Seq, Open, ...

base_url = "https://api.gdc.cancer.gov/"


with open('metadata.json') as f:
    metadata = json.load(f)

case_ids = []
disease_types = []
normal_file_ids = []
tumor_file_ids = []

#Get case ids for each file in metadata
for file in metadata:
    case_id = file['associated_entities'][0]['case_id']

#Get samples from case
    endpoint = "cases/" + case_id
    params = {
        "expand": "samples,samples.portions,samples.portions.analytes,samples.portions.analytes.aliquots"
    }
    response = requests.get(base_url + endpoint, params=params)
    case_data = response.json()
    samples = case_data.get("data", {}).get("samples", [])

    #Loop through each sample in the case to find the primary tumor sample
    tumor_sample_id = None
    priority = 5
    for sample in samples:
        submitter_id = sample.get("submitter_id")
        sample_id = sample.get("sample_id")
        #sample_type = sample.get("sample_type")
        tissue_type = sample.get("tissue_type")
        tumor_descriptor = sample.get("tumor_descriptor")
        
        #This should be the one with '01' in the name, otherwise we can filter by other criteria above (sample type, tissue type, tumor descriptor)
        if '01A' in submitter_id:
            tumor_sample_id = sample_id
            break
        elif '-01' in submitter_id and priority > 1:
            tumor_sample_id = sample_id
            priority = 1
        elif '01' in submitter_id and priority > 2:
            tumor_sample_id = sample_id
            priority = 2
        elif tissue_type == 'Tumor' and tumor_descriptor == 'Primary' and priority > 3:
            tumor_sample_id = sample_id
            priority = 3
        elif tissue_type == 'Tumor' and priority > 4:
            tumor_sample_id = sample_id
            priority = 4


    if tumor_sample_id is None:
        print(f'!!No associated sample for case {case_id}')
        continue

    #Filter the files associated with the primary tumor sample to find the right one (RNA-Seq TSV file)
    filters = {
        "op": "and",
        "content": [
            {
                "op": "in",
                "content": {
                    "field": "cases.samples.sample_id",
                    "value": [tumor_sample_id]
                }
            },
            {
                "op": "=",
                "content": {
                    "field": "experimental_strategy",
                    "value": "RNA-Seq"
                }
            },
            {
                "op": "=",
                "content": {
                    "field": "data_format",
                    "value": "TSV"
                }
            },

            {
                "op": "=",
                "content": {
                    "field": "access",
                    "value": "open"
                }
            }

        ]
    }

    params = {
        "filters": json.dumps(filters),
        "fields": "file_id,file_name,data_type,data_format,experimental_strategy,created_datetime,cases.samples.sample_id,cases.samples.submitter_id,cases.samples.sample_type,access,data_category,state,md5sum,file_size,platform",
        "format": "JSON",
        "size": "100"
    }

    response = requests.get(base_url + 'files', params=params)

    #Get file id associated with first hit of correct file:
    if len(response.json()['data']['hits']) != 0:
        tumor_file_ids.append(response.json()['data']['hits'][0]['file_id'])
        normal_file_ids.append(file['file_id'])
        disease_types.append(case_data['data']['disease_type'])
    #If we cant find any files with for that sample, just see if there's other files within that case
    else: 

        filters = {
        "op": "and",
        "content": [
            {
                "op": "in",
                "content": {
                    "field": "cases.case_id",
                    "value": [case_id]
                }
            },
            {
                "op": "=",
                "content": {
                    "field": "experimental_strategy",
                    "value": "RNA-Seq"
                }
            },
            {
                "op": "=",
                "content": {
                    "field": "data_format",
                    "value": "TSV"
                }
            },

            {
                "op": "=",
                "content": {
                    "field": "access",
                    "value": "open"
                }
            }

        ]
        }

        params = {
            "filters": json.dumps(filters),
            "fields": "file_id,file_name,data_type,data_format,experimental_strategy,created_datetime,cases.samples.sample_id,cases.samples.submitter_id,cases.samples.sample_type,access,data_category,state,md5sum,file_size,platform",
            "format": "JSON",
            "size": "100"
        }

        response = requests.get(base_url + 'files', params=params)


        if len(response.json()['data']['hits']) != 0:
            for hit in response.json()['data']['hits']:
                if hit['file_id'] != file['file_id']:
                    tumor_file_ids.append(hit['file_id'])
                    normal_file_ids.append(file['file_id'])
                    disease_types.append(case_data['data']['disease_type'])
                    print(hit['file_name'])
                    break
                else:
                    print('File ids same, skipping')
        else:
            print(f"!!Could not find any files for sample {tumor_sample_id}")

#Write file ids to json for download
tumor_dict = {"ids": tumor_file_ids}
normal_dict = {"ids": normal_file_ids}
with open('tumor_file_ids.json', 'w') as f:
    json.dump(tumor_dict, f)
with open('normal_file_ids.json', 'w') as f:
    json.dump(normal_dict, f)

#Json relating normal to tumor to disease type
normtumortype = {}
for i, (disease_type, tumor_file_id, normal_file_id) in enumerate(zip(disease_types, tumor_file_ids, normal_file_ids)):
    normtumortype[i] = [disease_type, tumor_file_id, normal_file_id]

with open('ground_truth.json', 'w') as f:
    json.dump(normtumortype, f)

print(f'Tumor files: {len(tumor_file_ids)}, normal files: {len(normal_file_ids)}, disease types: {len(disease_types)}')