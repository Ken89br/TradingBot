# strategy/ml_utils.py

import pandas as pd
import requests
import base64
import json

def upload_to_github(file_path, repo, path, token, commit_msg="Update model.pkl"):
    """
    Uploads or replaces a file in a GitHub repo.
    """
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"

    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # Get SHA of existing file (if any)
    sha = None
    headers = {"Authorization": f"token {token}"}
    r = requests.get(api_url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")

    data = {
        "message": commit_msg,
        "content": content,
        "branch": "main",
    }
    if sha:
        data["sha"] = sha

    r = requests.put(api_url, headers=headers, data=json.dumps(data))
    if r.status_code in [200, 201]:
        print("✅ model.pkl uploaded to GitHub.")
        return True
    else:
        print(f"❌ GitHub upload failed: {r.status_code} {r.text}")
        return False
    
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to the dataframe for training.
    Assumes df has columns: open, high, low, close, volume
    """

def download_model(url: str, dest: str = "model.pkl") -> bool:
    if not url:
        return False
    try:
        r = requests.get(url)
        with open(dest, "wb") as f:
            f.write(r.content)
        print(f"⬇️ Model downloaded from {url} to {dest}")
        return True
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        return False
        
    # Moving Averages
    df["sma_5"] = df["close"].rolling(window=5).mean()
    df["sma_10"] = df["close"].rolling(window=10).mean()

    # RSI (Relative Strength Index)
    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)

    avg_gain = up.rolling(window=14).mean()
    avg_loss = down.rolling(window=14).mean()
    rs = avg_gain / (avg_loss + 1e-6)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # MACD (12,26,9)
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    return df

def upload_model(model_path: str, upload_url: str) -> bool:
    """
    Upload a model file (e.g., model.pkl) to a cloud storage URL.
    The upload_url should be a valid pre-signed URL (Firebase, S3, etc.)
    """
    if not upload_url:
        print("⚠️ Skipping model upload — UPLOAD_MODEL_URL not set.")
        return False

    try:
        with open(model_path, "rb") as f:
            response = requests.put(upload_url, data=f)

        if response.status_code in (200, 201):
            print(f"✅ Model uploaded to {upload_url}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception during model upload: {e}")
        return False
    
