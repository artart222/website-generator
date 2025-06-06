from django.conf import settings
import django
from django.template import Context, Template

# mark_safe is for mixixng proccessed markdown with django template
import django.utils.safestring

from processor.markdown_processor import MarkdownProcessor
from core.page import Page
from utils.fs_manager import FileSystemManager


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

# --- Crucial Setup for Standalone DTL Usage ---
if not settings.configured:
    settings.configure(
        TEMPLATES=[  # This is the key setting
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                # 'DIRS': [],  # For file-based templates, list of directories
                # 'APP_DIRS': False, # Usually True in projects, False for simple standalone
                "OPTIONS": {
                    # 'debug': True, # Optional: for more detailed error messages during dev
                },
            }
        ]
        # You might need to add other minimal settings here if your template
        # uses features that depend on them, e.g., INSTALLED_APPS for some tags.
        # For basic rendering as in the example, TEMPLATES is usually enough.
    )
    django.setup()  # This initializes Django's settings and application registry
# --- End of Setup ---

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
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="code.css">
    <link rel="stylesheet" href="header.css">
    <title>{{ page_title|capfirst }}</title>
  </head>

  <body>
    <header class="navbar">
    <a href="#" class="logo">Logo</a>

    <input type="checkbox" id="menu-toggle" />

    <label for="menu-toggle" class="menu-icon">
      <span></span>
      <span></span>
      <span></span>
    </label>

    <ul class="menu">
      <li><a href="#">Home</a></li>
      <li><a href="#">About</a></li>
      <li><a href="#">Services</a></li>
      <li><a href="#">Portfolio</a></li>
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
      menuToggle.addEventListener('change', function () {
        if (this.checked) {
          document.body.classList.add('menu-open');
        } else {
          document.body.classList.remove('menu-open');
        }
      });
    </script>
  </body>
</html>
"""

# 2. Create a Template object
t = Template(template_string)

# 3. Define the context data
context_data = {"page_title": test_page.get_title(), "content": test_page.get_contex()}
c = Context(context_data)

# 4. Render the template with the context
rendered_html = t.render(c)

# 5. Print the output
print(rendered_html)

fs_handler.write_file("output.html", rendered_html)
