# File Sharing Tool

A small Flask-based web tool for uploading files, generating shareable download links, and optionally protecting downloads with a password.

## Features

- Upload any file type (PDF, images, videos, ZIP, etc.).
- Files are stored in an `uploads/` folder on the server.
- Each upload gets a unique shareable link of the form `/download/<file_id>`.
- Optional password protection using bcrypt hashing.
- Password is required before download if enabled.
- Basic security: `secure_filename`, fixed upload directory, 1 GB size limit, UUID-based IDs.
- Optional automatic expiration: links and files are cleaned up after 7 days when accessed.
- Simple, modern UI with upload progress bar.

## Project Structure

```text
file_share_tool/
├── app.py
├── requirements.txt
├── uploads/              # created automatically on first run
├── templates/
│   ├── upload.html
│   ├── password.html
│   └── success.html
├── static/
│   ├── style.css
│   └── upload.js
└── database.db           # created automatically on first run
```

## Local Setup Instructions

These commands assume you are in the `file_share_tool` directory and have Python 3.10+ installed.

### Step 1

```bash
python -m venv venv
```

### Step 2

On Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

### Step 3

Install dependencies:

```bash
pip install -r requirements.txt
```

### Step 4

Run the application:

```bash
python app.py
```

The server should start at:

`http://localhost:5000`

## Testing Guide

### Test 1: Upload file without password

1. Open `http://localhost:5000` in your browser.
2. Choose any file.
3. Leave the password field blank.
4. Click **Upload**.

**Expected result:** You see a success page with a shareable link. Opening the link starts the download directly without asking for a password.

### Test 2: Upload file with password

1. Open `http://localhost:5000`.
2. Choose a file.
3. Enter a password in the password field.
4. Click **Upload**.

**Expected result:** You see a success page with a shareable link. Opening the link shows a password page instead of downloading directly.

### Test 3: Wrong password

1. Perform **Test 2** to obtain a protected link.
2. Open the link in a browser.
3. Enter an incorrect password.

**Expected result:** The page shows an error message indicating the password is incorrect and allows retrying.

### Test 4: Correct password

1. Open the protected link again.
2. Enter the correct password used during upload.

**Expected result:** The file downloads successfully.

### Additional Behaviors

- If a file larger than 1 GB is selected, the client-side script will warn you, and the server enforces a 1 GB limit.
- Links older than 7 days are treated as expired; when accessed, the underlying file and record are deleted and an HTTP 410 (Gone) error is returned.

