# mSWE-GNN

This is the Doss-Gollin lab fork of the original repository for the paper "Multi-scale hydraulic graph neural networks for flood modelling" by Bentivoglio and coauthors.
Please refer to and cite the [original paper](https://nhess.copernicus.org/articles/25/335/2025/).

## Getting started

These instructions currently target the DesignSafe allocation to TACC, but can be adapted for other environments.

1. Create the environment and Jupyter kernel
    1. `chmod +x setup_venv.sh`
    2. `./setup_venv.sh`
2. Activate the `mswe-gnn-venv` environment
    1. `source mswe-gnn-venv/bin/activate`
3. Download the raw data
    1. `chmod +x download_data.sh`
    2. `./download_data.sh`
4. Turn the raw data into appropriate training data
    1. Run [`create_dataset.ipynb`](./database/create_dataset.ipynb) to create the training data.
5. Open [`main.ipynb`](./main.ipynb) and run

This is research code, modified by us who are not the original developers (though we will contribute back to their repository) so please use this model carefully!
