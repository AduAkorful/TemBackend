import os
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
ALLOWED_NON_EVM_EXTENSIONS = {".rs", ".wasm", ".py", ".cairo"}


def validate_extension(filename: str, allowed_extensions: set):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed.")


async def save_uploaded_file(file: UploadFile, subfolder: str) -> str:
    upload_dir = os.path.join("uploaded_contracts", subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        contents = await file.read()
        buffer.write(contents)
    return file_path


# Upload EVM
@router.post("/upload-evm")
async def upload_evm_contract(contract_file: UploadFile = File(...)):
    validate_extension(contract_file.filename, ALLOWED_EVM_EXTENSIONS)

    # Read the file into memory
    contents = await contract_file.read()

    # Upload to remote Docker container directly
    upload_to_remote_container_memory(contents, contract_file.filename, "evm")

    # Trigger the Docker test
    logs = trigger_docker_test(contract_file.filename, "evm")

    # Dynamically generate report filename from contract name
    base_name = Path(contract_file.filename).stem.strip()
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

    contents = await contract_file.read()
    upload_to_remote_container_memory(contents, contract_file.filename, "non-evm")

    logs = trigger_docker_test(contract_file.filename, "non-evm")

    base_name = Path(contract_file.filename).stem.strip()
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



@router.post("/upload-non-evm-algorand")
async def upload_algorand_contract(contract_file: UploadFile = File(...)):
    validate_extension(contract_file.filename, ALLOWED_NON_EVM_EXTENSIONS)

    contents = await contract_file.read()
    upload_to_remote_container_memory(contents, contract_file.filename, "non-evm")

    logs = trigger_docker_test(contract_file.filename, "non-evm")

    base_name = Path(contract_file.filename).stem.strip()
    report_filename = f"{base_name}-report.md"

    aggregated_content = fetch_from_remote_container(report_filename, "non-evm")

    #result = process_algorand_contract(contents, contract_file.filename)

    return JSONResponse(content={
        "message": "Algorand contract processed",
        "filename": contract_file.filename,
        "docker_logs": logs,
        "aggregated_report": aggregated_content,
        #"details": result
    })


@router.post("/upload-non-evm-starknet")
async def upload_starknet_contract(contract_file: UploadFile = File(...)):
    validate_extension(contract_file.filename, ALLOWED_NON_EVM_EXTENSIONS)

    contents = await contract_file.read()
    upload_to_remote_container_memory(contents, contract_file.filename, "non-evm")

    logs = trigger_docker_test(contract_file.filename, "non-evm")

    base_name = Path(contract_file.filename).stem.strip()
    report_filename = f"{base_name}-report.md"

    aggregated_content = fetch_from_remote_container(report_filename, "non-evm")

   # result = process_starknet_contract(contents, contract_file.filename)

    return JSONResponse(content={
        "message": "Starknet contract processed",
        "filename": contract_file.filename,
        "docker_logs": logs,
        "aggregated_report": aggregated_content,
        #"details": result
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
    base = Path(filename).stem.strip()
    report_filename = f"{base}-report.md"

    aggregated = fetch_from_remote_container(report_filename, "non-evm")
    
    return JSONResponse(
        content={"filename": filename, "aggregated_report": aggregated},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )


@router.get("/results/non-evm-algorand/{filename}")
async def get_algorand_test_results(filename: str):
    base = Path(filename).stem.strip()
    report_filename = f"{base}-report.md"

    aggregated = fetch_from_remote_container(report_filename, "non-evm-algorand")

    return JSONResponse(
        content={"filename": filename, "aggregated_report": aggregated},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )


@router.get("/results/non-evm-starknet/{filename}")
async def get_starknet_test_results(filename: str):
    base = Path(filename).stem.strip()
    report_filename = f"{base}-report.md"

    aggregated = fetch_from_remote_container(report_filename, "non-evm-starknet")

    return JSONResponse(
        content={"filename": filename, "aggregated_report": aggregated},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )



# Dummy processors
def process_evm_contract(file_contents: bytes, filename: str) -> dict:
    return {"contract_type": "evm", "filename": filename, "status": "processed"}


def process_non_evm_contract(file_contents: bytes, filename: str) -> dict:
    return {"contract_type": "non-evm", "filename": filename, "status": "processed"}
