# -*- coding: utf-8 -*-
import re
import os
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

TARGET_URLS = [
    ("Nanjing", "https://njggzy.nanjing.gov.cn/njweb/search/fullsearch.html?wd=%E5%8D%9A%E7%89%A9%E9%A6%86"),
    ("Jiangsu", "http://jsggzy.jszwfw.gov.cn/search/fullsearch.html?wd=%E5%8D%9A%E7%89%A9%E9%A6%86")
]

MUSEUM_KEYWORDS = ["博物馆", "展览馆", "文物", "文化遗产"]

def fetch_page(url):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "search-row"))
        )

        html_content = driver.page_source
        driver.quit()
        return html_content
    except Exception as e:
        print(f"请求过程中发生错误：{e}")
        return None

def parse_tenders(html_content, source):
    soup = BeautifulSoup(html_content, 'html.parser')
    tenders = []

    tender_items = soup.find_all('li', class_='search-row')
    for item in tender_items:
        title_tag = item.find('h2', class_='title')
        if title_tag and title_tag.find('a'):
            a_tag = title_tag.find('a')
            title = a_tag.get_text(strip=True)
            onclick = a_tag.get('onclick', '')
            href = a_tag.get('href', '')
            link = onclick.split("'")[5] if source == "Nanjing" else onclick.split("'")[1] if 'onclick' in a_tag.attrs else href
            if any(keyword in title for keyword in MUSEUM_KEYWORDS):
                tenders.append({
                    'title': title,
                    'link': link,
                    'date': item.find('span', class_='content-date').get_text(strip=True) if item.find('span', class_='content-date') else '未知日期',
                    'source': source
                })
    return tenders

def format_for_wechat(tenders):
    if not tenders:
        return "未找到博物馆相关的招标信息。"
    message = "博物馆相关招标信息更新：\n\n"
    for i, tender in enumerate(tenders, 1):
        message += f"{i}. {tender['title']}\n   来源: {tender['source']}\n   日期: {tender['date']}\n   链接: {tender['link']}\n\n"
    return message

def send_wechat_message(content):
    webhook_url = os.environ.get("WECHAT_WEBHOOK_URL")
    if not webhook_url:
        print("缺少 WECHAT_WEBHOOK_URL 配置")
        return
    data = {
        "msgtype": "text",
        "text": {"content": content}
    }
    try:
        resp = requests.post(webhook_url, json=data)
        resp.raise_for_status()
        print("企业微信消息发送成功")
    except Exception as e:
        print("发送失败：", e)

def main():
    all_tenders = []
    for source, url in TARGET_URLS:
        print(f"爬取 {source} 网站: {url}")
        html_content = fetch_page(url)
        if html_content:
            tenders = parse_tenders(html_content, source)
            if tenders:
                all_tenders.extend(tenders)
                print(f"从 {source} 找到 {len(tenders)} 条博物馆相关招标信息。")
            else:
                print(f"{source} 无相关信息。")
        else:
            print(f"无法访问 {source} 页面。")
    message = format_for_wechat(all_tenders)
    print(message)
    send_wechat_message(message)

if __name__ == "__main__":
    main()
