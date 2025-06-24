"""
learnit_load.py
"""

from learnit import LearnIt

# PATH_TO_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/Duale_Reihe_Biochemie.pdf"
#PATH_TO_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/Lüllmann_Rauch_Taschenlehrbuch_Histologie_2009.pdf"
PATH_TO_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/Silbernagl_Taschenatlas_Physiologie_8_Aufl_2012.pdf"


li = LearnIt.from_pdf(PATH_TO_PDF)   # uses store “test_VS”, id saved in .vector_store_ids/test_VS.id
pages_dir = li.slice_pdf(PATH_TO_PDF)
li.ingest_directory(pages_dir)