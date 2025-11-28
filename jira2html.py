# =====================================================
# Jira Offline Browser Generator
# 🔹 Supports Jara, Confluence local HTML smart mapping
# 🔹 Supports attachments and subtasks display
# 🔹 Home page sorted by the 4th column of issues.csv
# 🔹 Site-wide 9pt font, attachments do not display original URL
# =====================================================
import os
import json
import html
import re
import urllib.parse
from jira2markdown import convert
import markdown
import time

# ====== Path Configuration ======
BASE_DIR = r"D:\you_jara_dir" # Contains directories like issues, attachment, etc.
ISSUES_DIR = os.path.join(BASE_DIR, "issues")
ATTACH_DIR = os.path.join(BASE_DIR, "attachment")
OUTPUT_DIR = os.path.join(BASE_DIR, "offline_site")
DOCS_DIRS = [
    r"D:\you_confluence_docs"
]

# ====== Index Database ======
DOC_INDEX = {}
DOC_INDEX_NOEXT = {}
DOC_SIMPLIFIED = {}
import os
import json
import html
import re
import urllib.parse

# Load author mapping table (path can be modified)
#[
#    {
#        "nick_name": "jhon",
#        "long_name": "John Smith",
#        "dir_name": "~johnsmith"
#    },
#   {
#        "nick_name": "mary",
#        "long_name": "Mary Johnson",
#        "dir_name": "~maryjhonson"
#    }
#]
AUTHOR_MAP_PATH = os.path.join(BASE_DIR, "jira2html_name_mapping.json")
AUTHOR_MAP = {}
if os.path.exists(AUTHOR_MAP_PATH):
    with open(AUTHOR_MAP_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        AUTHOR_MAP = {
            item['nick_name'].lower(): item['long_name']
            for item in data
            if 'nick_name' in item and 'long_name' in item
        }
# ← 1️⃣ Put ensure_dir here
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
# ← 2️⃣ Followed by build_doc_index() / find_local_html and other functions
def simplify_key(name):
    ...
# =====================================================
# 🔍 HTML Document Name Standardization
# =====================================================
def simplify_key(name):
    name = urllib.parse.unquote(name).lower()
    name = name.replace(".html", "")
    name = re.sub(r'[\s+\-%()（）_/]', '', name)
    return name

# =====================================================
# 📚 Build HTML File Index Database
# =====================================================
def build_doc_index():
    print("\n🛠 Scanning document directories, building HTML index...\n")
    for base_dir in DOCS_DIRS:
        if not os.path.isdir(base_dir):
            continue
       
        for root, dirs, files in os.walk(base_dir):
            for fname in files:
                if fname.lower().endswith(".html"):
                    full_path = os.path.join(root, fname)
                    key1 = fname
                    key2 = fname.replace(".html", "")
                    key3 = simplify_key(fname)
                    DOC_INDEX[key1] = full_path
                    DOC_INDEX_NOEXT[key2] = full_path
                    DOC_SIMPLIFIED[key3] = full_path
    print(f"📚 HTML mapping built successfully, identified {len(DOC_INDEX)} files.\n")

def resolve_forward_html(html_path):
    """
    Detect if the exported Confluence HTML is a "Forward to page" redirect page,
    If so, automatically locate the real target page.
    """
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            text = f.read()
        # 1️⃣ Detect meta refresh redirect (common format)
        m = re.search(r'<meta http-equiv="refresh"[^>]+url=([^">]+)', text, flags=re.I)
        if m:
            target = urllib.parse.unquote(m.group(1).strip())
        else:
            # 2️⃣ Detect <a href="xxx.html">Redirecting...</a> method
            m2 = re.search(r'<a\s+href="([^"]+\.html)"', text, flags=re.I)
            target = urllib.parse.unquote(m2.group(1).strip()) if m2 else None
        if target:
            new_path = os.path.join(os.path.dirname(html_path), target)
            if os.path.exists(new_path):
                return new_path # 🔥 Return the real content page
    except Exception:
        pass
    return html_path # Non-redirect page → Return as is

# =====================================================
# 🔗 Intelligently find local HTML files based on title / pageId
# =====================================================
def find_local_html(name):
    if not name:
        return None
    raw = urllib.parse.unquote(name).strip()
    raw_noext = raw.replace(".html", "")
    # ⬇ Step-by-step matching: original → no extension → simplified
    for key in (raw, raw_noext, simplify_key(raw)):
        candidate = DOC_INDEX.get(key) or DOC_INDEX_NOEXT.get(key) or DOC_SIMPLIFIED.get(key)
        if candidate and os.path.exists(candidate):
            return resolve_forward_html(candidate)
    return None

# =====================================================
# Convert local file path to file:/// protocol clickable link
# =====================================================
def format_local_link(path):
    if not path:
        return None
    path = os.path.abspath(path).replace("\\", "/")
    return f"file:///{urllib.parse.quote(path)}"

# =====================================================
# 🔗 Replace Confluence links with local file:///
# =====================================================
def replace_confluence_links(text):
    if not text:
        return text
    # 🔹 /display/TSGEN/M22-VPN+List
    pattern1 = re.compile(
        r'https?://docs\.xxx\.com/display/'
        r'[A-Za-z0-9]+/'
        r'([^\]\s\)]+(?: [^\]\s\)]+)*)'
    )
    def repl1(m):
        raw_title = urllib.parse.unquote(m.group(1)).replace("+", " ").strip()
        if not raw_title.lower().endswith(".html"):
            raw_title += ".html"
        local = find_local_html(raw_title)
        return format_local_link(local) or m.group(0)
    text = pattern1.sub(repl1, text)
    # 🔹 pageId=123456
    pattern2 = re.compile(
        r'https?://docs\.xxx\.com/pages/viewpage\.action\?pageId=(\d+)'
    )
    def repl2(m):
        filename = m.group(1) + ".html"
        local = find_local_html(filename)
        return format_local_link(local) or m.group(0)
    text = pattern2.sub(repl2, text)
    # 🔹 Remove trailing symbols ] ) ， 。 etc.
    text = re.sub(r'(file:///[^\s\]]+)([\]\)\uff0c\u3002>】]+)', r'\1', text)
    return text

import urllib.parse
def file_url_to_text(path):
    """
    Convert file:///D%3A/... to D:\... plain text path
    """
    if not path or not path.startswith("file:///"):
        return path
   
    decoded = urllib.parse.unquote(path.replace("file:///", ""))
    decoded = decoded.replace("/", "\\") # Convert to Windows path
    return decoded
def find_local_image(filename):
    """
    Recursively search for an image file in the attachment directory, return file:/// path
    """
    for root, dirs, files in os.walk(ATTACH_DIR):
        for f in files:
            if f.lower() == filename.lower():
                return "file:///" + os.path.abspath(os.path.join(root, f)).replace("\\", "/")
    return None

from jira2markdown import convert
import markdown
def jira_wiki_to_html(jira_text):
    """
    Convert Jira Wiki text → High-quality HTML
    """
    # 1️⃣ JiraWiki → Markdown
    try:
        md_text = convert(jira_text)
    except Exception:
        md_text = jira_text
    # 2️⃣ Markdown → HTML (Enable extensions for code highlighting, tables, etc.)
    html_text = markdown.markdown(
        md_text,
        extensions=[
            'fenced_code', # Support ``` code ```
            'tables', # Support tables
            'codehilite', # Code highlighting
            'nl2br', # Automatic line breaks
            'toc', # Automatically generate table of contents
        ]
    )
   
    return html_text

# =====================================================
# 📝 Description field formatting (Supports HTML links & line breaks)
# =====================================================
def format_description(text, image_map=None):
    if not text:
        return ""
   
    # Ensure image_map is at least a dictionary to avoid NoneType issues
    if image_map is None:
        image_map = {}
       
    # 1️⃣ First process Confluence links
    text = replace_confluence_links(text)
    # 5️⃣ Identify author tags [~pinyin] → Display Chinese name
    def repl_author(m):
        pingyin = m.group(1).lower()
        if pingyin in AUTHOR_MAP:
            return f"{AUTHOR_MAP[pingyin]}[~{pingyin}]"
        else:
            return m.group(0) # Keep as is
    text = re.sub(r'\[~([a-zA-Z]+)\]', repl_author, text)
    # 🔹 Jira Wiki → Markdown → HTML
    try:
        text = jira_wiki_to_html(text)
    except:
        pass
   
    # 2️⃣ Escape HTML
    #text = html.escape(text, quote=True)
    '''
    # 3️⃣ Support Jira color format {color:#FF0000}text{color}
    def repl_color(m):
        color = m.group(1)
        text_inner = m.group(2)
        return f"<span style='color:{color}'>{text_inner}</span>"
    text = re.sub(
        r'\{color:(#[0-9A-Fa-f]{6})\}(.*?)\{color\}',
        repl_color,
        text,
        flags=re.DOTALL
    )
    # 🔹Identify Jira image syntax: !filename.png! → <img src="...">
   
    def repl_image(m):
        fname = m.group(1).strip()
        local_path = find_local_image(fname)
        if local_path:
            return f"<img src='{local_path}' style='max-width:600px;'><br>"
        else:
            return f"[Image not found: {fname}]"
    text = re.sub(r'!\s*([^!]+?\.(?:png|jpg|jpeg|gif))\s*!', repl_image, text, flags=re.IGNORECASE)
    '''
    '''
    # Replace the image part in format_description() with:
    def repl_image(m):
        fname = m.group(1).strip().lower()
        if fname in image_map:
            local_path = file_url_to_text(image_map[fname]) # Display as D:\...
            return (f"<img src='{local_path}' style='max-width:600px;'><br>"
                    f"{local_path}<br>")
        else:
            return f"[Image not found: {fname}]<br>"
    # Replace !xxx.png! syntax
    text = re.sub(r'!\s*([^!]+\.(?:png|jpg|jpeg|gif))\s*!', repl_image, text, flags=re.IGNORECASE)
    '''
    # 4️⃣ Identify and display file:/// links
    text = re.sub(r'(file:///[^ <]+)', r'<a href="\1">\1</a>', text)
    '''
    # Original format_description ending
    text = text.replace("\n", "<br>")
    '''
    # ➕ Add this line to automatically convert file:/// links to plain text paths
    text = re.sub(r'file:///[^ <]+', lambda m: file_url_to_text(m.group(0)), text)
    '''
    # 🔹 Remove possible spaces, <br>, carriage returns, tabs, etc. at the end inside href quotes
    text = re.sub(
        r'href="([^"<]+?)\s*(?:<br>|<br/>|</br>)?\s*"',
        r'href="\1"',
        text,
        flags=re.IGNORECASE
    )
    '''
    return text

# =====================================================
# 📎 Attachment path parsing (local)
# =====================================================
def jira_url_to_attachment(content_url):
    if not content_url:
        return None, None, None
    m = re.search(r'/attachment/(\d+)/(.+)$', content_url)
    if not m:
        return None, None, None
    att_id = m.group(1)
    filename = urllib.parse.unquote(m.group(2))
    local_path = os.path.join(ATTACH_DIR, att_id, filename)
    return local_path, filename, att_id

# =====================================================
# 📄 Read Issue JSON data
# =====================================================
def load_issue(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    fields = data.get("fields", {})
    def get(*keys, default=""):
        cur = fields
        for k in keys:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k, {})
        return cur if cur else default
    return {
        "key": data.get("key", ""),
        "summary": get("summary"),
        "description": get("description"),
        "status": get("status", "name"),
        "assignee": get("assignee", "displayName"),
        "created": get("created"),
        "attachments": fields.get("attachment", []),
        "subtasks": fields.get("subtasks", [])
    }

# =====================================================
# 🧾 Get sorting order from issues.csv (4th column)
# =====================================================
def load_issue_order_from_csv():
    csv_path = os.path.join(BASE_DIR, "issues.csv")
    if not os.path.exists(csv_path):
        return []
   
    order_list = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 4:
                order_list.append(parts[3].strip().upper())
    return order_list

# =====================================================
# 🏗️ Generate single Issue HTML page
# =====================================================
def build_issue_page(issue, out_dir):
    # Add this at the beginning of build_issue_page(issue, out_dir):
    # Build mapping table for image filename → local file:/// full path
    image_map = {}
    for att in issue.get("attachments", []):
        filename = att.get("filename", "")
        content_url = att.get("content", "")
        # Parse attachment local path
        local_path, _, _ = j