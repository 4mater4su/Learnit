from learnit import LearnIt

PATH_TO_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/M10_komplett.pdf"

li = LearnIt.from_pdf(PATH_TO_PDF)   # uses store “test_VS”, id saved in .vector_store_ids/test_VS.id

li.search_and_copy_page(
    query="Den Aufbau von echten Gelenken beschreiben",
    dest_dir="/Users/robing/Desktop/projects/Learnit/testing"
)