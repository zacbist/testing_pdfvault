# pdf-vault

Encrypted document processing pipeline. Decrypts and analyzes PDF document data stored in a local SQLite database, with decryption keys managed by a remote key server.

## Overview

Documents are pre-processed into structured feature sets (text extraction, metadata, page counts, category labels) and stored as encrypted blobs in a SQLite database. Each document has a unique Fernet encryption key held by a centralized key server. The pipeline fetches keys over HTTPS with basic auth, decrypts documents locally, and writes analysis results to CSV.

## Setup

```bash
pip install -r requirements.txt
```

Copy `config.ini.example` to `config.ini` and set the key server URL and credentials for your environment. The bundled `ssl/server-ca.pem` provides the CA certificate for the default key server.

## Usage

```bash
python main.py
```

The script reads all document records from `store.db`, fetches the per-document decryption key from the key server (20 concurrent threads), decrypts each blob, loads the pre-extracted document features, and writes a summary CSV to `output/results.csv`.

## Project Structure

```
pdf-vault/
├── main.py              # Multi-threaded document processor
├── config.ini           # Key server configuration
├── requirements.txt     # Python dependencies
├── store.db             # SQLite database with encrypted document records
├── ssl/
│   └── server-ca.pem    # CA certificate for the key server
└── output/
    └── results.csv      # Generated analysis results
```

## Configuration

`config.ini` settings:

| Key | Description |
|-----|-------------|
| `url` | Key server endpoint URL |
| `user` | Basic auth username |
| `pass` | Basic auth password |
| `ca_bundle` | Path to CA certificate bundle for TLS verification |

## Dependencies

- **cryptography** — Fernet symmetric encryption for document decryption
- **joblib** — Efficient serialization and loading of pre-processed document features
- **pypdf** — PDF text extraction and page counting
- **requests** — HTTP client for key server communication
