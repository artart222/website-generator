from processor.markdown_processor import MarkdownProcessor
from core.page import Page
from utils.fs_manager import FileSystemManager
from engines.django_engine import DjangoTemplateEngine
from core.config import Config

import logging
import argparse

debug = True


# NOTE: A Basic logger has been added.
# TODO: In future complete this
# I initilize logger 2 times
# first time for having basic logging in utils.py and config.py
# And second time for having better logging in other parts of program
# I do this because I want to have both good logging
# And logging in utils.py and config.py
# Parse CLI flag
parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
args = parser.parse_args()
if args.debug:
    debug = True
elif args.no_debug:
    debug = False

# Setup logging
logging.basicConfig(
    # TODO: Fix this
    level=logging.DEBUG if debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.debug("Debug mode is active")
logging.info("App started")

app_config = Config()
app_config.load("./configfsaf.yaml")

debug = app_config.get("debug", True)

# Setup logging
logging.basicConfig(
    # TODO: Fix this
    level=logging.DEBUG if debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.debug("Debug mode is active")
logging.info("Initilizing new logger")

fs_handler = FileSystemManager()
md_processor = MarkdownProcessor(["extra", "meta", "codehilite"])
test_page = Page()
test_page.read_source_file("main.md")
test_page.process_content(md_processor)
test_page.process_metadata(md_processor)


template_engine = DjangoTemplateEngine()
context_data = {"page_title": test_page.get_title(), "content": test_page.get_contex()}
rendered_html = template_engine.render("post", context_data)


fs_handler.write_file("output/output.html", rendered_html)
fs_handler.copy_directory("styles", "output/styles")
