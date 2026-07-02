#!/usr/bin/env python3
import os
import sys
import email
from email import policy
from bs4 import BeautifulSoup
import weasyprint


def extract_html_from_mhtml(mhtml_path):
    with open(mhtml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    html_content = None
    for part in msg.walk():
        if part.get_content_type() == 'text/html':
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            try:
                html_content = payload.decode(charset, errors='replace')
            except:
                html_content = payload.decode('utf-8', errors='replace')
            break
    
    if html_content is None:
        for part in msg.walk():
            if part.get_content_maintype() == 'text':
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                try:
                    html_content = payload.decode(charset, errors='replace')
                except:
                    html_content = payload.decode('utf-8', errors='replace')
                break
    
    return html_content


def clean_wechat_article(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    title = ''
    title_elem = soup.find(id='activity-name') or soup.find(class_='rich_media_title') or soup.find('h1')
    if title_elem:
        title = title_elem.get_text(strip=True)
    
    author = ''
    author_elem = soup.find(id='js_name') or soup.find(class_='rich_media_meta_nickname')
    if author_elem:
        author = author_elem.get_text(strip=True)
    
    publish_date = ''
    date_elem = soup.find(id='publish_time') or soup.find(class_='rich_media_meta_text')
    if date_elem:
        publish_date = date_elem.get_text(strip=True)
    
    content_elem = soup.find(id='js_content')
    
    if content_elem is None:
        content_elem = soup.find(class_='rich_media_content')
    
    if content_elem is None:
        content_elem = soup.find('article') or soup.find('main') or soup.body or soup
    
    for tag in content_elem.find_all(['script', 'style']):
        tag.decompose()
    
    for img in content_elem.find_all('img'):
        src = img.get('src', '')
        data_src = img.get('data-src', '')
        
        if data_src and not src:
            img['src'] = data_src
        
        final_src = img.get('src', '')
        
        if 'data:image/svg+xml' in final_src or 'data:image/gif;base64' in final_src:
            img.decompose()
            continue
        
        if not final_src:
            img.decompose()
    
    for tag in content_elem.find_all(['section', 'div', 'span', 'p']):
        text = tag.get_text(strip=True)
        if not text and not tag.find('img'):
            tag.decompose()
    
    result_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
@page {
    size: A4;
    margin: 2.5cm;
}
body {
    font-family: "Noto Sans CJK SC", "Noto Sans CJK", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    font-size: 12pt;
    line-height: 1.8;
    color: #333;
    background: white;
}
h1 {
    font-size: 22pt;
    font-weight: bold;
    text-align: center;
    margin-bottom: 16pt;
    color: #1a1a1a;
}
h2 {
    font-size: 16pt;
    font-weight: bold;
    margin-top: 24pt;
    margin-bottom: 12pt;
    color: #222;
    border-bottom: 2px solid #eee;
    padding-bottom: 6pt;
}
h3 {
    font-size: 14pt;
    font-weight: bold;
    margin-top: 20pt;
    margin-bottom: 10pt;
    color: #333;
}
p {
    margin: 10pt 0;
    text-align: justify;
    text-indent: 2em;
}
em.meta {
    display: block;
    text-align: center;
    font-size: 10pt;
    color: #666;
    margin-bottom: 20pt;
}
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 16pt auto;
    border-radius: 4px;
}
a {
    color: #0066cc;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
strong, b {
    font-weight: bold;
    color: #1a1a1a;
}
blockquote {
    border-left: 4px solid #0066cc;
    padding-left: 16pt;
    margin: 16pt 0;
    color: #555;
    font-style: italic;
}
</style>
</head>
<body>
'''
    
    if title:
        result_html += f'<h1>{title}</h1>\n'
    if author or publish_date:
        meta_parts = []
        if author:
            meta_parts.append(author)
        if publish_date:
            meta_parts.append(publish_date)
        result_html += f'<em class="meta">{" · ".join(meta_parts)}</em>\n'
    result_html += str(content_elem)
    result_html += '''</body></html>'''
    
    return result_html


def convert_mhtml_to_pdf(mhtml_path, output_dir=None):
    filename = os.path.basename(mhtml_path)
    pdf_filename = os.path.splitext(filename)[0] + '.pdf'
    
    if output_dir:
        pdf_path = os.path.join(output_dir, pdf_filename)
    else:
        pdf_path = os.path.splitext(mhtml_path)[0] + '.pdf'
    
    print(f'正在转换: {filename}')
    
    try:
        html_content = extract_html_from_mhtml(mhtml_path)
        if not html_content:
            print(f'  警告: 未找到 HTML 内容')
            return False
        
        cleaned_html = clean_wechat_article(html_content)
        
        html_doc = weasyprint.HTML(string=cleaned_html)
        html_doc.write_pdf(pdf_path)
        
        size = os.path.getsize(pdf_path)
        print(f'  成功: {pdf_filename} ({size/1024:.1f} KB)')
        return True
    except Exception as e:
        print(f'  失败: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print('用法: python convert_mhtml_to_pdf.py <mhtml文件或目录>')
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if os.path.isfile(input_path):
        convert_mhtml_to_pdf(input_path)
    elif os.path.isdir(input_path):
        mhtml_files = [
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith('.mhtml') or f.lower().endswith('.mht')
        ]
        
        if not mhtml_files:
            print(f'目录中未找到 mhtml 文件: {input_path}')
            sys.exit(1)
        
        print(f'找到 {len(mhtml_files)} 个 mhtml 文件\n')
        
        success_count = 0
        for mhtml_file in sorted(mhtml_files):
            if convert_mhtml_to_pdf(mhtml_file):
                success_count += 1
            print()
        
        print(f'转换完成: {success_count}/{len(mhtml_files)} 成功')
    else:
        print(f'路径不存在: {input_path}')
        sys.exit(1)


if __name__ == '__main__':
    main()
