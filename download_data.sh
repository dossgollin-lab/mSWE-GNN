#!/bin/bash
# download_data.sh
# Downloads all data files from the Zenodo record and extracts them.

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

# --- Configuration ---
# The record ID for the dataset on Zenodo
RECORD_ID="13326595"
# The API URL to get record details
API_URL="https://zenodo.org/api/records/${RECORD_ID}"
# The target directory structure required by the program
TARGET_DIR="database" # Changed to download directly into 'database'

echo "--- Preparing data directory: ./${TARGET_DIR}/ ---"
# Create the data directory if it doesn't already exist
mkdir -p "${TARGET_DIR}"

echo "--- Fetching all download URLs from Zenodo API ---"
# Use wget, grep, and cut to find all "self" links, which are the download URLs.
DOWNLOAD_URLS=$(wget -qO- "${API_URL}" | grep -o '"self": "[^"]*content"' | cut -d '"' -f 4)

# Check if any URLs were found
if [ -z "${DOWNLOAD_URLS}" ]; then
    echo "ERROR: Could not find any download URLs from the Zenodo API. Aborting."
    exit 1
fi

echo "Found URLs to download:"
echo "${DOWNLOAD_URLS}"

# --- Download all files ---
# Create a temporary directory to download the archives into.
TEMP_DOWNLOAD_DIR=$(mktemp -d)
echo "Downloading files to temporary directory: ${TEMP_DOWNLOAD_DIR}"
echo "${DOWNLOAD_URLS}" | while read -r url; do
    # Use --content-disposition to save the file with its original name from the server.
    wget --content-disposition --directory-prefix="${TEMP_DOWNLOAD_DIR}" "${url}"
done

# --- Extract and clean up all downloaded archives ---
echo "--- Extracting all datasets into ${TARGET_DIR} ---"
for zip_file in "${TEMP_DOWNLOAD_DIR}"/*.zip; do
  echo "Extracting ${zip_file}..."
  # Unzip the file's contents directly into the final target directory
  unzip -o "${zip_file}" -d "${TARGET_DIR}"
done

echo "--- Cleaning up temporary files ---"
rm -r "${TEMP_DOWNLOAD_DIR}"

echo "--- ✅ Data download and setup complete! ---"
echo "All datasets are ready in the ./${TARGET_DIR}/ directory."