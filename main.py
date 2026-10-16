import os
import io
import csv
import sqlite3
import joblib
import requests
import concurrent.futures
from cryptography.fernet import Fernet
from pypdf import PdfReader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "store.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
OUTPUT_PATH = os.path.join(BASE_DIR, "output", "results.csv")
NUM_THREADS = 20


def load_config():
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return {
        "server_url": cfg.get("keyserver", "url"),
        "auth_user": cfg.get("keyserver", "user"),
        "auth_pass": cfg.get("keyserver", "pass"),
        "ca_bundle": cfg.get("keyserver", "ca_bundle", fallback=None),
    }


def fetch_key(file_name, server_link, config):
    ca = config["ca_bundle"]
    if ca and os.path.isfile(ca):
        verify = ca
    elif ca:
        verify = False
    else:
        verify = True
    resp = requests.get(
        server_link,
        auth=(config["auth_user"], config["auth_pass"]),
        params={"file_name": file_name},
        verify=verify,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["key"]


def decrypt_and_load(file_name, encrypted_data, server_link, config):
    key = fetch_key(file_name, server_link, config)
    fernet = Fernet(key.encode())
    raw = fernet.decrypt(encrypted_data)
    doc = joblib.load(io.BytesIO(raw))
    return doc


def extract_pdf_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text, len(reader.pages)


def process_row(row, config):
    file_name, encrypted_data, server_link = row
    try:
        doc = decrypt_and_load(file_name, encrypted_data, server_link, config)
        page_count = doc.get("pages", 0)
        word_count = len(doc.get("text", "").split())
        category = doc.get("category", "unknown")
        return {
            "file": file_name,
            "status": "ok",
            "pages": page_count,
            "words": word_count,
            "category": category,
        }
    except Exception as e:
        return {"file": file_name, "status": "error", "message": str(e)}


def write_results(results):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "status", "pages", "words", "category", "message"])
        writer.writeheader()
        for r in sorted(results, key=lambda x: x["file"]):
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})


def main():
    config = load_config()

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT file_name, file_data, server_link FROM documents"
    ).fetchall()
    conn.close()

    print(f"Processing {len(rows)} documents with {NUM_THREADS} threads...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as pool:
        futures = {pool.submit(process_row, row, config): row[0] for row in rows}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            if result["status"] == "ok":
                print(f"  {result['file']}: {result['pages']} pages, {result['words']} words, {result['category']}")
            else:
                print(f"  {result['file']}: ERROR - {result['message']}")

    write_results(results)
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\nDone: {ok}/{len(results)} documents processed successfully.")
    print(f"Results written to {OUTPUT_PATH}")
    return results


if __name__ == "__main__":
    main()
