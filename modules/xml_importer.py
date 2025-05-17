import os
import requests
from bs4 import BeautifulSoup

WORDPRESS_LOGIN = "https://smartmoneymomma.org/wp-login.php"
USERNAME = "akhilamadireddy1987@gmail.com"
PASSWORD = "AjahRudhr@2019"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

def login(session):
    payload = {
        'log': USERNAME,
        'pwd': PASSWORD,
        'wp-submit': 'Log In',
        'redirect_to': 'https://smartmoneymomma.org/wp-admin/',
        'testcookie': '1'
    }
    res = session.post(WORDPRESS_LOGIN, headers=HEADERS, data=payload)
    return "dashboard" in res.text.lower()

def import_posts_from_xml(xml_path):
    with open(xml_path, 'r', encoding='utf-8') as file:
        content = file.read()

    posts = content.split('<item>')
    posts = posts[1:]  # Skip header

    with requests.Session() as session:
        if not login(session):
            print("[✖] Login failed.")
            return

        print("[✓] Logged into WordPress.")
        for idx, post in enumerate(posts[:5]):  # Limit import to 5 for safety
            title = post.split('<title>')[1].split('</title>')[0]
            body = post.split('<content:encoded>')[1].split('</content:encoded>')[0]
            nonce_page = session.get("https://smartmoneymomma.org/wp-admin/post-new.php")
            soup = BeautifulSoup(nonce_page.text, 'html.parser')
            nonce = soup.find("input", {"id": "_wpnonce"})

            payload = {
                'post_title': title,
                'content': body,
                '_wpnonce': nonce['value'],
                '_wp_http_referer': '/wp-admin/post-new.php',
                'user_ID': '1',
                'action': 'editpost',
                'originalaction': 'editpost',
                'post_author': '1',
                'post_type': 'post',
                'original_post_status': 'auto-draft',
                'referredby': 'https://smartmoneymomma.org/wp-admin/post-new.php',
                'save': 'Publish',
                'post_status': 'publish',
            }

            r = session.post("https://smartmoneymomma.org/wp-admin/post.php", headers=HEADERS, data=payload)
            if "Post published" in r.text:
                print(f"[✓] Imported: {title}")
            else:
                print(f"[!] Failed to import: {title}")

if __name__ == "__main__":
    xml_file = "smartmoneymomma.WordPress.2025-04-22.xml"
    import_posts_from_xml(xml_file)
