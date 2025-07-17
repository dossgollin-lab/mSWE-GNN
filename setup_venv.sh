#!/bin/bash
# setup_venv.sh
# A script to create a Python virtual environment and install all dependencies using pip.

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

# Define the name of the virtual environment directory
VENV_NAME="mswe-gnn-venv"

echo "--- Creating Python virtual environment: ${VENV_NAME} ---"
# Create the virtual environment
python3 -m venv ${VENV_NAME}

echo "--- Activating virtual environment ---"
# Activate the environment
source ${VENV_NAME}/bin/activate

# Pip will now use the standard PyPI index and find a version of PyG compatible
# with the PyTorch you just installed.
echo "--- Installing PyG, Lightning, and remaining project dependencies ---"
pip install \
  torch-geometric \
  lightning \
  numpy \
  scipy \
  pandas \
  scikit-learn \
  networkx \
  fiona \
  shapely \
  netcdf4 \
  xarray \
  pyyaml \
  tqdm \
  wandb \
  ipykernel \
  nbformat \
  matplotlib \
  triangle \
  perlin-noise \
  meshkernel

echo "--- Creating Jupyter kernel for the environment ---"
# Create the ipykernel for Jupyter notebooks
python3 -m ipykernel install --user --name mSWE-GNN --display-name "mSWE-GNN"

echo "--- ✅ Setup complete! ---"
echo "To use the environment, run: source ${VENV_NAME}/bin/activate"