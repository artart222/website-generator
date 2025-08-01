from processor.markdown_processor import MarkdownProcessor
from core.page import Page
from utils.fs_manager import FileSystemManager
from engines.django_engine import DjangoTemplateEngine

# TODO: Remove this, this was just a test
# import sys
# RED = "\033[91m"  # Red
# YELLOW = "\033[33m"  # Yellow
# GREEN = "\033[32m"  # Green
# RESET = "\033[0m"  # Default color
# print(
#     f"{GREEN}Converting process has been done succefuly{RESET}",
#     file=sys.stderr,
# )

fs_handler = FileSystemManager()
md_processor = MarkdownProcessor(["extra", "meta", "codehilite"])
test_page = Page()
test_page.read_source_file("main.md")
test_page.process_content(md_processor)
test_page.process_metadata(md_processor)


template_engine = DjangoTemplateEngine()
context_data = {"page_title": test_page.get_title(), "content": test_page.get_contex()}
rendered_html = template_engine.render("post", context_data)

print(rendered_html)

fs_handler.write_file("output/output.html", rendered_html)
fs_handler.copy_file("styles", "output/styles")
