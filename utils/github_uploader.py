import base64
import json
import requests
import os

def upload_to_github(file_path, repo, path, token, commit_msg="Update file"):
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"

    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # Check if file exists
    headers = {"Authorization": f"token {token}"}
    r = requests.get(api_url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    data = {
        "message": commit_msg,
        "content": content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    r = requests.put(api_url, headers=headers, data=json.dumps(data))
    if r.status_code in (200, 201):
        print(f"✅ Uploaded {file_path} to GitHub.")
        return True
    else:
        print(f"❌ Upload failed: {r.status_code} {r.text}")
        return False
