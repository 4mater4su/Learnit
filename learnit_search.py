"""
learnit_search.py
"""

from learnit import LearnIt

#PATH_TO_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/M10_komplett.pdf"
#PATH_TO_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/Schmidt-Lang-Heckmann-Physiologie-des-Menschen.pdf"
PATH_TO_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/Prometheus_allgemeine_Anatomie_und_Bewegungssystem.pdf"


li = LearnIt.from_pdf(PATH_TO_PDF)   # uses store “test_VS”, id saved in .vector_store_ids/test_VS.id

li.search_and_copy_pages(
    query="Lage und Funktion des Oberschenkelkniestreckers (M. quadriceps femoris) als Beispiel für eine gelenksübergreifende Muskelwirkung beschreiben und erläutern können.",
    dest_dir="/Users/robing/Desktop/learnit_testing"
)