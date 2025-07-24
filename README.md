# mSWE-GNN

This is the Doss-Gollin lab fork of the original repository for the paper "Multi-scale hydraulic graph neural networks for flood modelling" by Bentivoglio and coauthors.
Please refer to and cite the [original paper](https://nhess.copernicus.org/articles/25/335/2025/).

## Getting started

These instructions currently target the DesignSafe allocation to TACC, but can be adapted for other environments.

1. Create the environment and Jupyter kernel
   A) Using the provided bash script
    1. `chmod +x setup_venv.sh`
    2. `./setup_venv.sh`
   B) Using conda
    1. conda env create -f environment.yml
    2. conda activate mswe-gnn
   C) Using a plain venv + pip
    1. python3 -m venv mswe-gnn
    3. activate:
       Linux/maxOS/WSL/Git Bash: source mswe-gnn/bin/activate
       Windows PowerShell: .\mswe-gnn\Scripts\Activate.ps1
    5. pip install --upgrade pip
    6. pip install -r requirement.txt
   *ATTENTION:
    1. Make sure you end up with meshkernel==3.0.0
    2. python 3.13 may not enable using GPU
3. Activate the `mswe-gnn-venv` environment
    1. `source mswe-gnn-venv/bin/activate`
4. Download the raw data
    1. `chmod +x download_data.sh`
    2. `./download_data.sh`
5. Turn the raw data into appropriate training data
    1. Run [`create_dataset.ipynb`](./database/create_dataset.ipynb) to create the training data.
6. Open [`main.ipynb`](./main.ipynb) and run

This is research code, modified by us who are not the original developers (though we will contribute back to their repository) so please use this model carefully!
