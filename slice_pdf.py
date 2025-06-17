from PyPDF2 import PdfReader, PdfWriter


def slice_pdf(input_pdf: str, output_pdf: str, start: int, end: int) -> None:
    """
    Extract pages [start .. end] (1-based) from *input_pdf* and write to *output_pdf*.
    """
    reader = PdfReader(input_pdf)
    if start < 1 or end > len(reader.pages) or start > end:
        raise ValueError(
            f"Ungültiger Bereich {start}-{end} für PDF mit {len(reader.pages)} Seiten."
        )

    writer = PdfWriter()
    for i in range(start - 1, end):
        writer.add_page(reader.pages[i])
    with open(output_pdf, "wb") as fh:
        writer.write(fh)