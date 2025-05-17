import os
import xml.etree.ElementTree as ET

XML_PATH = "smartmoneymomma.WordPress.2025-04-22.xml"

def extract_titles_from_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    namespace = {
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'wp': 'http://wordpress.org/export/1.2/'
    }

    items = root.findall('./channel/item')
    posts = []

    for item in items:
        post_type = item.find('wp:post_type', namespace)
        if post_type is not None and post_type.text == 'post':
            title = item.find('title').text or "Untitled"
            content = item.find('content:encoded', namespace).text or ""
            posts.append((title.strip(), content.strip()))

    return posts

def save_posts_to_text(posts, output_folder="imported_posts"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for i, (title, content) in enumerate(posts):
        filename = os.path.join(output_folder, f"post_{i+1}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\n\n{content}\n")

if __name__ == "__main__":
    posts = extract_titles_from_xml(XML_PATH)
    if posts:
        save_posts_to_text(posts)
        print(f"[✓] {len(posts)} blog articles exported to /imported_posts folder.")
    else:
        print("[!] No posts found in the XML.")
