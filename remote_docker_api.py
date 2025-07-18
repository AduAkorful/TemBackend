import io
import tarfile
import requests
import os
import time

# Docker API expects archive at this endpoint
DOCKER_API_URL = "https://dockerapi.smarttesthub.live/containers/evm-container/archive?path=/app/input"
HEADERS = {"Content-Type": "application/x-tar"}


def upload_to_remote_container_memory(file_bytes: bytes, filename: str, contract_type: str):
    """
    Uploads a contract file as a .tar archive to the Docker container's /app/input directory.
    """
    tar_stream = io.BytesIO()

    # Create in-memory .tar file
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(file_bytes)
        tar.addfile(tarinfo, io.BytesIO(file_bytes))

    tar_stream.seek(0)

    # PUT to Docker API
    response = requests.put(DOCKER_API_URL, headers=HEADERS, data=tar_stream)

    if response.status_code != 200:
        raise Exception(f"Upload to Docker failed: {response.status_code} - {response.text}")

    return {"status": "success", "message": "File uploaded and extracted to container"}


def trigger_docker_test(filename: str, contract_type: str) -> str:
    """
    Sends a request to the Docker container to begin testing the uploaded contract.
    """
    url = f"{DOCKER_API_URL}/trigger-test"
    data = {
        "filename": filename,
        "contract_type": contract_type
    }
    response = requests.post(url, json=data)
    if response.status_code != 200:
        return f"❌ Remote execution failed: {response.status_code} - {response.text}"
    return f"✅ Test triggered:\n{response.text}"


def fetch_from_remote_container(report_filename: str, contract_type: str, timeout: int = 60) -> str:
    """
    Polls the appropriate Docker container for a specific contract report file.
    Extracts and returns the .md report from the tarball when it's ready.
    """

    # Mapping contract types to their respective container names
    container_map = {
        "evm": "evm-container",
        "non-evm": "non-evm-container",
        "non-evm-algorand": "non-evm-algorand",
        "non-evm-starknet": "non-evm-starknet"
    }

    container = container_map.get(contract_type)
    if not container:
        return f"❌ Unknown contract type '{contract_type}'"

    url = (
        f"https://dockerapi.smarttesthub.live"
        f"/containers/{container}/archive"
        f"?path=/app/logs/reports/{report_filename}"
    )

    print(f"🧭 Looking for report in container type: {contract_type}")
    print(f"🌐 Full Docker API polling URL: {url}")

    for second in range(timeout):
        resp = requests.get(url)
        if resp.status_code == 200:
            print(f"📦 TAR file received. Extracting '{report_filename}'…")
            try:
                tar_stream = io.BytesIO(resp.content)
                with tarfile.open(fileobj=tar_stream, mode="r:*") as tar:
                    member = next((m for m in tar.getmembers() if m.name.endswith(report_filename)), None)
                    if member:
                        extracted = tar.extractfile(member)
                        if extracted:
                            return extracted.read().decode()
                        else:
                            return f"❌ Could not extract '{report_filename}' from tar."
                    return f"❌ '{report_filename}' not found inside TAR."
            except Exception as e:
                return f"❌ Error extracting TAR: {e}"

        elif resp.status_code == 404:
            print(f"⌛ Waiting for file ({second + 1}/{timeout})…")
        else:
            return f"❌ Unexpected response {resp.status_code}: {resp.text}"

        time.sleep(1)

    return f"❌ File '{report_filename}' not available after {timeout}s."
