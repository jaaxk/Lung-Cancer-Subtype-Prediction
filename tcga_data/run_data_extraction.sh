#!/bin/bash

#Needs metadata.json file in the current directory
#This file should contain metadata for all normal samples that we wish to find their corresponding tumor sample and download

if ! [ -f "./normal_file_ids.json" ]; then
    echo "Getting tumor file ids from TCGA"
    python get_paired_files.py
fi

if ! [ -d "./normal_files" ]; then
    #Download normal and tumor files separately
    echo "Downloading files"
    curl --request POST --header "Content-Type: application/json" --data @normal_file_ids.json https://api.gdc.cancer.gov/data -o normal_files.tar.gz
    curl --request POST --header "Content-Type: application/json" --data @tumor_file_ids.json https://api.gdc.cancer.gov/data -o tumor_files.tar.gz

    #Extract into tumor and normal directory
    echo "Extracting files"
    tar -xzf normal_files.tar.gz --strip-components=2 
    tar -xzf tumor_files.tar.gz --strip-components=2 
fi
