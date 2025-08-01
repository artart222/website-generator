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


# 1. The template string
template_string = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="styles/styles.css">
    <link rel="stylesheet" href="styles/code.css">
    <title>{{ page_title|capfirst }}</title>
  </head>

  <body>
    <header class="navbar">
        <a href="#" class="logo">MySite</a>
        <!-- The hamburger menu checkbox and icon (only visible on mobile) -->
        <input type="checkbox" id="menu-toggle">
        <label for="menu-toggle" class="menu-icon">
            <span></span>
            <span></span>
            <span></span>
        </label>
        
        <!-- THE SINGLE navigation list for both mobile and desktop -->
        <ul class="nav-menu">
            <li><a href="#">Home</a></li>
            <li><a href="#">Blog</a></li>
            <li><a href="#">About</a></li>
            <li><a href="#">Contact</a></li>
        </ul>
    </header>
    <main>
      {{content|safe}}
    </main>
    <script>
      // This small script toggles a class on the body to prevent scrolling when the menu is open.
      // The menu's open/close logic itself remains pure CSS.
      const menuToggle = document.getElementById('menu-toggle');
        menuToggle.addEventListener('change', function() {
        document.body.classList.toggle('menu-open', this.checked);
      });
    </script>
  </body>
</html>
"""

template_engine = DjangoTemplateEngine()
context_data = {"page_title": test_page.get_title(), "content": test_page.get_contex()}
rendered_html = template_engine.render_from_string(template_string, context_data)

# 5. Print the output
print(rendered_html)

fs_handler.write_file("output/output.html", rendered_html)
fs_handler.copy_file("styles", "output/styles")
