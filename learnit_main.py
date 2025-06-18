from learnit import LearnIt

li = LearnIt("Experiment_VS")

# turn big PDF into 1-page files
pages_dir = li.slice_pdf("/Users/robing/Desktop/projects/Learnit/PDFs/test.pdf")

# upload them
li.ingest_directory(pages_dir)

# semantic query → copy first cited page into a study folder
copied = li.search_and_copy_page(
    query="Wie sieht die Diagnostik bei einer Schenkelhalsfraktur aus?",
    dest_dir="/Users/robing/Desktop/projects/Learnit/archive/goal1"
)
print("Copied to:", copied)
