"""Web interface: complete end-to-end workflow with the synthetic demo, in English and Japanese."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from medvision_qa import web
from medvision_qa.history import History

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "synthetic_demo"
CSV_NAMES = ("ground_truth.csv", "preds_v1.csv", "preds_v2.csv")


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def client(data_dir):
    return TestClient(web.create_app(data_dir), follow_redirects=False)


def demo_files(overrides=None):
    overrides = overrides or {}
    contents = {name: overrides.get(name, (DEMO / name).read_bytes()) for name in ("config.toml",) + CSV_NAMES}
    files = [("config", ("config.toml", contents["config.toml"], "application/toml"))]
    files += [("data_files", (name, contents[name], "text/csv")) for name in CSV_NAMES]
    return files


def run_ids(data_dir):
    runs = data_dir / "runs"
    return sorted(p.name for p in runs.iterdir()) if runs.exists() else []


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'enctype="multipart/form-data"' in response.text
    assert "No evaluations yet." in response.text
    assert "<script" not in response.text


def test_end_to_end_workflow(client, data_dir):
    response = client.post("/evaluations", files=demo_files())
    assert response.status_code == 303
    location = response.headers["location"]
    run_id = location.rsplit("/", 1)[1]
    assert web.RUN_ID_PATTERN.fullmatch(run_id)

    page = client.get(location)
    assert page.status_code == 200
    assert "SATISFIED" in page.text and "C1" in page.text and "C3" in page.text
    assert "demo-cnn-v1" in page.text

    report = client.get(f"/evaluations/{run_id}/report")
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("text/html")
    assert "form-action 'none'" in report.headers["content-security-policy"]
    assert run_id in report.text and "What This Report Cannot Establish" in report.text

    download = client.get(f"/evaluations/{run_id}/report/download")
    assert download.status_code == 200
    assert f'filename="VVR-{run_id}.html"' in download.headers["content-disposition"]
    assert download.content == report.content

    home = client.get("/")
    assert f'href="/evaluations/{run_id}"' in home.text

    record = History(data_dir / "history.sqlite").get(run_id)
    assert record.status == "completed" and record.n_cases == 872
    assert record.config_sha256 in report.text


def test_uploaded_files_stored_byte_identical(client, data_dir):
    response = client.post("/evaluations", files=demo_files())
    run_id = response.headers["location"].rsplit("/", 1)[1]
    for name in ("config.toml",) + CSV_NAMES:
        assert (data_dir / "runs" / run_id / name).read_bytes() == (DEMO / name).read_bytes()


def test_invalid_data_rejected_and_traced_without_keeping_files(client, data_dir):
    lines = (DEMO / "preds_v2.csv").read_bytes().splitlines(keepends=True)
    response = client.post("/evaluations", files=demo_files({"preds_v2.csv": b"".join(lines[:-1])}))
    assert response.status_code == 422
    assert "Evaluation rejected" in response.text and "same_cases" in response.text
    assert run_ids(data_dir) == []  # no data kept
    (record,) = History(data_dir / "history.sqlite").recent()
    assert record.status == "rejected" and "same_cases" in record.error
    assert "evaluation rejected" in client.get("/").text


def test_invalid_config_rejected(client, data_dir):
    config = (DEMO / "config.toml").read_bytes().replace(b"seed = 20261029", b"seed = -1")
    response = client.post("/evaluations", files=demo_files({"config.toml": config}))
    assert response.status_code == 422 and "seed" in response.text
    assert run_ids(data_dir) == []


def test_config_cannot_reach_outside_workspace(client, data_dir):
    config = (DEMO / "config.toml").read_bytes().replace(b'"ground_truth.csv"', b'"../../ground_truth.csv"')
    response = client.post("/evaluations", files=demo_files({"config.toml": config}))
    assert response.status_code == 422 and "leaves the configuration folder" in response.text


def test_config_referencing_missing_upload(client):
    files = [f for f in demo_files() if f[1][0] != "preds_v2.csv"]
    response = client.post("/evaluations", files=files)
    assert response.status_code == 422 and "file not found" in response.text


@pytest.mark.parametrize("bad_name", ["../evil.csv", "sub/x.csv", "..\\x.csv", ".hidden.csv", "a b.csv"])
def test_unsafe_filenames_rejected(client, data_dir, bad_name):
    files = demo_files()
    files[1] = ("data_files", (bad_name, files[1][1][1], "text/csv"))
    response = client.post("/evaluations", files=files)
    assert response.status_code == 400
    assert "File name refused" in response.text
    assert run_ids(data_dir) == []


def test_wrong_extension_and_duplicates_rejected(client):
    files = demo_files()
    files[1] = ("data_files", ("ground_truth.txt", files[1][1][1], "text/plain"))
    assert ".csv extension expected" in client.post("/evaluations", files=files).text
    files = demo_files()
    files[2] = ("data_files", ("ground_truth.csv", files[2][1][1], "text/csv"))
    assert "Duplicate file names" in client.post("/evaluations", files=files).text


def test_missing_files_rejected(client):
    response = client.post("/evaluations", files=[("data_files", ("a.csv", b"x", "text/csv"))])
    assert response.status_code == 400 and "configuration" in response.text
    response = client.post("/evaluations", files=demo_files()[:1])
    assert response.status_code == 400 and "No CSV file" in response.text


def test_too_many_files_rejected(client):
    files = demo_files() + [("data_files", (f"x{i}.csv", b"a", "text/csv")) for i in range(2)]
    response = client.post("/evaluations", files=files)
    assert response.status_code == 400 and "maximum" in response.text


def test_oversized_file_rejected(client, data_dir, monkeypatch):
    monkeypatch.setattr(web, "MAX_FILE_BYTES", 1000)
    response = client.post("/evaluations", files=demo_files())
    assert response.status_code == 413
    assert run_ids(data_dir) == []


@pytest.mark.parametrize("path", [
    "/evaluations/not-a-uuid",
    "/evaluations/00000000-0000-4000-8000-000000000000",
    "/evaluations/00000000-0000-4000-8000-000000000000/report",
    "/evaluations/..%2F..%2Fhistory.sqlite/report",
    "/examples/generate.py",
    "/examples/..%2F..%2Fpyproject.toml",
])
def test_unknown_resources_not_found(client, path):
    assert client.get(path).status_code == 404


def test_example_files_downloadable(client):
    response = client.get("/examples/preds_v1.csv")
    assert response.status_code == 200
    assert response.content == (DEMO / "preds_v1.csv").read_bytes()
    assert "attachment" in response.headers["content-disposition"]


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'none'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"


def test_no_api_docs_exposed(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_user_text_escaped_in_pages(client):
    config = (DEMO / "config.toml").read_bytes().replace(
        b"Synthetic demonstration", b"<img src=x onerror=alert(1)>")
    response = client.post("/evaluations", files=demo_files({"config.toml": config}))
    location = response.headers["location"]
    for page in (client.get(location).text, client.get("/").text):
        assert "<img src=x" not in page and "&lt;img src=x" in page


def test_history_lists_most_recent_first(client):
    first = client.post("/evaluations", files=demo_files()).headers["location"]
    second = client.post("/evaluations", files=demo_files()).headers["location"]
    home = client.get("/").text
    assert home.index(second) < home.index(first)
    assert len(re.findall(r'href="/evaluations/[0-9a-f-]{36}"', home)) == 2


# --- Japanese interface ------------------------------------------------------------------

def test_home_page_in_japanese(client):
    page = client.get("/?lang=ja").text
    assert '<html lang="ja">' in page and "新しい評価" in page and "評価はまだありません。" in page
    assert 'action="/evaluations?lang=ja"' in page
    assert 'href="/" lang="en"' in page  # switch back to English


def test_unknown_language_falls_back_to_english(client):
    page = client.get("/?lang=xx").text
    assert '<html lang="en">' in page and "New evaluation" in page


def test_end_to_end_workflow_in_japanese(client):
    response = client.post("/evaluations?lang=ja", files=demo_files())
    assert response.status_code == 303 and response.headers["location"].endswith("?lang=ja")
    run_id = response.headers["location"].split("/")[2].split("?")[0]

    page = client.get(response.headers["location"]).text
    assert "総合判定:" in page and "SATISFIED（基準充足）" in page
    assert "下限" in page  # criterion justification rendered in Japanese
    assert f'href="/evaluations/{run_id}/report?lang=ja"' in page

    report = client.get(f"/evaluations/{run_id}/report?lang=ja")
    assert '<html lang="ja">' in report.text and "総合判定:" in report.text
    english = client.get(f"/evaluations/{run_id}/report")
    assert '<html lang="en">' in english.text

    download = client.get(f"/evaluations/{run_id}/report/download?lang=ja")
    assert f'filename="VVR-{run_id}.ja.html"' in download.headers["content-disposition"]
    assert download.content == report.content


def test_rejection_messages_in_both_languages(client):
    lines = (DEMO / "preds_v2.csv").read_bytes().splitlines(keepends=True)
    files = demo_files({"preds_v2.csv": b"".join(lines[:-1])})
    response = client.post("/evaluations?lang=ja", files=files)
    assert response.status_code == 422
    assert "評価は受け付けられませんでした" in response.text and "にある症例が、このファイルにありません" in response.text
    assert "評価不可:" in client.get("/?lang=ja").text
    assert "evaluation rejected: [same_cases]" in client.get("/").text


def test_upload_errors_in_japanese(client):
    response = client.post("/evaluations?lang=ja", files=demo_files()[:1])
    assert response.status_code == 400 and "CSV ファイルが指定されていません。" in response.text
