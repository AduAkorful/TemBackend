import os
import glob
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from remote_docker_api import (
    trigger_docker_test,
    upload_to_remote_container_memory,
    fetch_from_remote_container
)

router = APIRouter()

ALLOWED_EVM_EXTENSIONS = {".sol", ".txt"}
ALLOWED_NON_EVM_EXTENSIONS = {".rs", ".wasm"}

def validate_extension(filename: str, allowed_extensions: set):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed.")

def cleanup_old_artifacts(contract_name: str, contract_type: str):
    """
    Removes old contract files and reports for the given contract base name and type.
    This prevents old test results from being included in new reports.
    """
    # Define remote paths: input and reports
    # Here we only clean up local uploaded_contracts/ (optionally add remote cleanup if needed)
    local_input_dir = os.path.join("uploaded_contracts", contract_type)
    local_report_dir = os.path.join("test_summaries", contract_type)
    os.makedirs(local_input_dir, exist_ok=True)
    os.makedirs(local_report_dir, exist_ok=True)
    for pattern in [
        os.path.join(local_input_dir, f"{contract_name}*"),
        os.path.join(local_report_dir, f"{contract_name}*")
    ]:
        for file in glob.glob(pattern):
            try:
                os.remove(file)
            except Exception:
                pass

# Upload EVM
@router.post("/upload-evm")
async def upload_evm_contract(contract_file: UploadFile = File(...)):
    validate_extension(contract_file.filename, ALLOWED_EVM_EXTENSIONS)

    # Clean up old artifacts for this contract before new upload
    base_name = Path(contract_file.filename).stem.strip().lower()
    cleanup_old_artifacts(base_name, "evm")

    # Read the file into memory
    contents = await contract_file.read()

    # Upload to remote Docker container directly
    upload_to_remote_container_memory(contents, contract_file.filename, "evm")

    # Trigger the Docker test
    logs = trigger_docker_test(contract_file.filename, "evm")

    # Dynamically generate report filename from contract name
    report_filename = f"{base_name}-report.md"

    # Fetch the specific report
    aggregated_content = fetch_from_remote_container(report_filename, "evm")

    result = process_evm_contract(contents, contract_file.filename)

    return JSONResponse(content={
        "message": "EVM contract processed",
        "filename": contract_file.filename,
        "docker_logs": logs,
        "aggregated_report": aggregated_content,
        "details": result
    })

# Upload Non-EVM
@router.post("/upload-non-evm")
async def upload_non_evm_contract(contract_file: UploadFile = File(...)):
    validate_extension(contract_file.filename, ALLOWED_NON_EVM_EXTENSIONS)

    base_name = Path(contract_file.filename).stem.strip().lower()
    cleanup_old_artifacts(base_name, "non-evm")

    contents = await contract_file.read()
    upload_to_remote_container_memory(contents, contract_file.filename, "non-evm")

    logs = trigger_docker_test(contract_file.filename, "non-evm")

    report_filename = f"{base_name}-report.md"

    aggregated_content = fetch_from_remote_container(report_filename, "non-evm")

    result = process_non_evm_contract(contents, contract_file.filename)

    return JSONResponse(content={
        "message": "Non-EVM contract processed",
        "filename": contract_file.filename,
        "docker_logs": logs,
        "aggregated_report": aggregated_content,
        "details": result
    })

# Results for EVM
@router.get("/results/{filename}")
async def get_test_results(filename: str):
    base = Path(filename).stem.strip().lower()
    report_filename = f"{base}-report.md"
    aggregated = fetch_from_remote_container(report_filename, "evm")
    return JSONResponse(
        content={"filename": filename, "aggregated_report": aggregated},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )

# Results for Non-EVM
@router.get("/results/non-evm/{filename}")
async def get_non_evm_test_results(filename: str):
    base = Path(filename).stem.strip().lower()
    report_filename = f"{base}-report.md"
    aggregated = fetch_from_remote_container(report_filename, "non-evm")
    return JSONResponse(
        content={"filename": filename, "aggregated_report": aggregated},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )

# Dummy processors
def process_evm_contract(file_contents: bytes, filename: str) -> dict:
    return {"contract_type": "evm", "filename": filename, "status": "processed"}

def process_non_evm_contract(file_contents: bytes, filename: str) -> dict:
    return {"contract_type": "non-evm", "filename": filename, "status": "processed"}
