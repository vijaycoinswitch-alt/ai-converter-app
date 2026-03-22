
import os
import io
import json
import zipfile
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:5000"
USERNAME = "admin"          # change if needed
PASSWORD = "1234"           # change if needed

TEST_DIR = Path("test_files")

TEST_CASES = [
    {
        "name": "Merge PDF",
        "url": f"{BASE_URL}/api/merge",
        "files": ["sample1.pdf", "sample2.pdf"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "Split PDF",
        "url": f"{BASE_URL}/api/split",
        "files": ["sample1.pdf"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "Compress PDF",
        "url": f"{BASE_URL}/api/compress",
        "files": ["sample1.pdf"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "JPG to PDF",
        "url": f"{BASE_URL}/api/jpg-to-pdf",
        "files": ["sample.jpg"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "PDF to Word",
        "url": f"{BASE_URL}/api/pdf-to-word",
        "files": ["sample1.pdf"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "Word to PDF",
        "url": f"{BASE_URL}/api/word-to-pdf",
        "files": ["sample.docx"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "Excel to PDF",
        "url": f"{BASE_URL}/api/excel-to-pdf",
        "files": ["sample.xlsx"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "PDF to JPG",
        "url": f"{BASE_URL}/api/pdf-to-jpg",
        "files": ["sample1.pdf"],
        "data": {},
        "expect_download": True,
    },
    {
        "name": "Remove Pages",
        "url": f"{BASE_URL}/api/remove-pages",
        "files": ["sample1.pdf"],
        "data": {"pages": "1"},
        "expect_download": True,
    },
    {
        "name": "Extract Pages",
        "url": f"{BASE_URL}/api/extract-pages",
        "files": ["sample1.pdf"],
        "data": {"pages": "1"},
        "expect_download": True,
    },
    {
        "name": "Rotate PDF",
        "url": f"{BASE_URL}/api/rotate",
        "files": ["sample1.pdf"],
        "data": {"angle": "90"},
        "expect_download": True,
    },
    {
        "name": "Add Watermark",
        "url": f"{BASE_URL}/api/add-watermark",
        "files": ["sample1.pdf"],
        "data": {"text": "TEST WATERMARK"},
        "expect_download": True,
    },
    {
        "name": "Protect PDF",
        "url": f"{BASE_URL}/api/protect",
        "files": ["sample1.pdf"],
        "data": {"password": "1234"},
        "expect_download": True,
    },
]

RESULTS_FILE = "test_results.json"


def print_line(char="=", n=70):
    print(char * n)


def login(session: requests.Session) -> bool:
    print_line()
    print("LOGIN TEST")
    print_line()

    resp = session.post(
        f"{BASE_URL}/login",
        data={"username": USERNAME, "password": PASSWORD},
        allow_redirects=True,
        timeout=60,
    )

    ok = resp.status_code == 200
    print(f"Status Code: {resp.status_code}")
    print(f"Final URL   : {resp.url}")
    print(f"Login Result: {'PASS' if ok else 'FAIL'}")
    return ok


def logout(session: requests.Session) -> bool:
    print_line()
    print("LOGOUT TEST")
    print_line()

    resp = session.get(f"{BASE_URL}/logout", allow_redirects=True, timeout=60)
    ok = resp.status_code == 200
    print(f"Status Code : {resp.status_code}")
    print(f"Final URL   : {resp.url}")
    print(f"Logout Result: {'PASS' if ok else 'FAIL'}")
    return ok


def build_files_payload(file_names):
    payload = []
    opened = []
    for name in file_names:
        path = TEST_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Missing test file: {path}")
        f = open(path, "rb")
        opened.append(f)
        payload.append(("files[]", (name, f)))
    return payload, opened


def verify_download(session: requests.Session, download_url: str):
    full_url = f"{BASE_URL}{download_url}" if download_url.startswith("/") else download_url
    resp = session.get(full_url, timeout=120)

    if resp.status_code != 200:
        return False, f"Download failed with status {resp.status_code}"

    content_type = resp.headers.get("Content-Type", "")
    size = len(resp.content)
    if size == 0:
        return False, "Downloaded file is empty"

    if "application/json" in content_type:
        return False, f"Expected file, got JSON: {resp.text[:200]}"

    return True, f"Downloaded OK ({size} bytes, {content_type})"


def test_one(session: requests.Session, case: dict):
    print_line("-")
    print(f"TEST: {case['name']}")
    print_line("-")

    files_payload, opened_files = build_files_payload(case["files"])

    try:
        resp = session.post(
            case["url"],
            files=files_payload,
            data=case.get("data", {}),
            timeout=300,
        )
    finally:
        for f in opened_files:
            f.close()

    result = {
        "name": case["name"],
        "endpoint": case["url"],
        "status_code": resp.status_code,
        "pass": False,
        "details": "",
    }

    try:
        data = resp.json()
    except Exception:
        data = None

    print(f"Status Code: {resp.status_code}")

    if resp.status_code != 200:
        body_preview = resp.text[:300]
        result["details"] = f"HTTP {resp.status_code}: {body_preview}"
        print("Result     : FAIL")
        print(f"Details    : {result['details']}")
        return result

    if not data:
        result["details"] = "Response is not valid JSON"
        print("Result     : FAIL")
        print(f"Details    : {result['details']}")
        return result

    if data.get("error"):
        result["details"] = data["error"]
        print("Result     : FAIL")
        print(f"Details    : {result['details']}")
        return result

    if case.get("expect_download"):
        download_url = data.get("download_url")
        if not download_url:
            result["details"] = f"download_url missing in response: {data}"
            print("Result     : FAIL")
            print(f"Details    : {result['details']}")
            return result

        ok, msg = verify_download(session, download_url)
        result["pass"] = ok
        result["details"] = msg
        print(f"Download   : {download_url}")
        print(f"Result     : {'PASS' if ok else 'FAIL'}")
        print(f"Details    : {msg}")
        return result

    if data.get("success") is True:
        result["pass"] = True
        result["details"] = "Success JSON returned"
        print("Result     : PASS")
        return result

    result["details"] = f"Unexpected response: {data}"
    print("Result     : FAIL")
    print(f"Details    : {result['details']}")
    return result


def main():
    if not TEST_DIR.exists():
        print(f"ERROR: test folder not found: {TEST_DIR.resolve()}")
        print("Create a folder named 'test_files' and place your sample files inside it.")
        return

    session = requests.Session()
    all_results = []

    try:
        login_ok = login(session)
        all_results.append({"name": "Login", "pass": login_ok})

        if not login_ok:
            print("\nLogin failed. Stopping tests.")
        else:
            for case in TEST_CASES:
                try:
                    result = test_one(session, case)
                except Exception as e:
                    result = {
                        "name": case["name"],
                        "endpoint": case["url"],
                        "status_code": None,
                        "pass": False,
                        "details": str(e),
                    }
                    print("Result     : FAIL")
                    print(f"Details    : {e}")
                all_results.append(result)

            logout_ok = logout(session)
            all_results.append({"name": "Logout", "pass": logout_ok})

    finally:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print_line()
        print(f"Saved results to {RESULTS_FILE}")
        print_line()

        passed = sum(1 for r in all_results if r.get("pass"))
        total = len(all_results)
        print(f"FINAL: {passed}/{total} tests passed")


if __name__ == "__main__":
    main()
