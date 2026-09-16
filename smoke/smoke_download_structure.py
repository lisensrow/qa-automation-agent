import base64
import hashlib
from io import BytesIO

from pypdf import PdfWriter

from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


CSV_BYTES = b"name,value\nalpha,1\nbeta,2\n"
pdf_writer = PdfWriter()
pdf_writer.add_blank_page(width=72, height=72)
pdf_stream = BytesIO()
pdf_writer.write(pdf_stream)
PDF_BYTES = pdf_stream.getvalue()

session = BrowserSession()
try:
    session._ensure_started()
    html = """
        <button onclick="download('report.csv', 'text/csv', '__CSV_B64__')">
          Download CSV
        </button>
        <button onclick="download('report.pdf', 'application/pdf', '__PDF_B64__')">
          Download PDF
        </button>
        <script>
          function download(name, type, b64) {
            const bytes = Uint8Array.from(atob(b64), ch => ch.charCodeAt(0));
            const blob = new Blob([bytes], {type});
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = name;
            document.body.appendChild(link);
            link.click();
            link.remove();
          }
        </script>
    """.replace(
        "__CSV_B64__", base64.b64encode(CSV_BYTES).decode("ascii")
    ).replace(
        "__PDF_B64__", base64.b64encode(PDF_BYTES).decode("ascii")
    )
    session.page.set_content(html)
    csv_download = session.download_semantic(
        "Download CSV", "report.csv", "text", hashlib.sha256(CSV_BYTES).hexdigest()
    )
    assert csv_download["download_status"] == "verified", csv_download
    csv_id = csv_download["download_id"]
    csv_result = session.verify_download_structure_semantic(
        csv_id, "csv", ["name", "value"], min_rows=2, max_rows=2,
    )
    assert csv_result["verification_status"] == "verified", csv_result
    assert csv_result["row_count"] == 2, csv_result
    assert "headers" not in csv_result
    assert session.verify_download_structure_semantic(
        csv_id, "csv", ["wrong", "value"], min_rows=2
    )["verification_status"] == "mismatch"
    assert session.verify_download_structure_semantic(
        "/opt/uqa/secrets/password.txt", "csv", ["name"]
    )["error"] == "download_id_unknown"

    pdf_download = session.download_semantic(
        "Download PDF", "report.pdf", "pdf", hashlib.sha256(PDF_BYTES).hexdigest()
    )
    assert pdf_download["download_status"] == "verified", pdf_download
    pdf_id = pdf_download["download_id"]
    pdf_result = session.verify_download_structure_semantic(
        pdf_id, "pdf", expected_pages=1,
    )
    assert pdf_result["verification_status"] == "verified", pdf_result
    assert pdf_result["page_count"] == 1, pdf_result
    assert session.verify_download_structure_semantic(
        pdf_id, "pdf", expected_pages=2
    )["verification_status"] == "mismatch"
    assert classify_tool_action(
        "browser_verify_download_structure_semantic", {}
    ) == "observe"
    assert any(
        item["function"]["name"] == "browser_verify_download_structure_semantic"
        for item in TOOLS
    )
finally:
    session.close()

print("download structure smoke: PASS")
