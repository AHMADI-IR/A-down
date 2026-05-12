#!/usr/bin/env python3
"""
Telegram Power Downloader
دانلود خودکار از تلگرام با قابلیت فشرده‌سازی پیشرفته
"""

import os
import re
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

class TelegramPowerDownloader:
    def __init__(self, output_dir="downloads", max_workers=3):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.downloaded_files = []
        
    def extract_post_info(self, url):
        """استخراج اطلاعات پست از لینک تلگرام"""
        patterns = [
            r't\.me/([^/]+)/(\d+)',
            r'telegram\.me/([^/]+)/(\d+)',
            r'https?://t\.me/([^/]+)/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        raise ValueError(f"❌ لینک نامعتبر: {url}")
    
    def get_telegram_page(self, channel, post_id):
        """دریافت صفحه پست با تلاش چندباره"""
        urls_to_try = [
            f"https://t.me/{channel}/{post_id}?embed=1",
            f"https://t.me/s/{channel}/{post_id}",
            f"https://telegram.me/{channel}/{post_id}"
        ]
        
        for url in urls_to_try:
            try:
                response = self.session.get(url, timeout=20)
                if response.status_code == 200:
                    return response.text
            except:
                continue
        raise Exception("امکان اتصال به تلگرام وجود ندارد")
    
    def extract_media_urls(self, html_content):
        """استخراج لینک فایل‌ها از صفحه"""
        # الگوهای مختلف برای پیدا کردن فایل
        patterns = [
            r'href="(https://[^"]+telegram[^"]+\.(mp4|mp3|jpg|png|gif|pdf|zip|rar|exe))"',
            r'src="(https://[^"]+telegram[^"]+\.(jpg|png|gif))"',
            r'data-document-thumbnail="([^"]+)"',
            r'href="(/file/[^"]+)"'
        ]
        
        urls = []
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match[0]
                if url.startswith('/file/'):
                    url = 'https://t.me' + url
                if url.startswith('//'):
                    url = 'https:' + url
                if 'telegram' in url or 'tg' in url:
                    urls.append(url)
        
        # حذف تکراری‌ها
        return list(set(urls))
    
    def download_single_file(self, url, filepath, retry=3):
        """دانلود یک فایل با قابلیت تلاش مجدد"""
        for attempt in range(retry):
            try:
                print(f"⬇️  دانلود: {filepath.name}")
                response = self.session.get(url, stream=True, timeout=60)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\r📊 پیشرفت: {percent:.1f}%", end='')
                
                print(f"\n✅ ذخیره شد: {filepath.name}")
                return True
                
            except Exception as e:
                print(f"\n⚠️ تلاش {attempt+1}/{retry} ناموفق: {e}")
                time.sleep(2)
        
        print(f"❌ دانلود نشد: {url}")
        return False
    
    def download_post(self, url):
        """دانلود کامل یک پست تلگرام"""
        print("\n" + "="*60)
        print("🚀 Telegram Power Downloader")
        print("="*60)
        
        # استخراج اطلاعات
        channel, post_id = self.extract_post_info(url)
        print(f"📺 کانال: @{channel}")
        print(f"🆔 پست: {post_id}")
        
        # دریافت صفحه
        html_content = self.get_telegram_page(channel, post_id)
        
        # ایجاد پوشه
        post_folder = self.output_dir / f"{channel}_{post_id}"
        post_folder.mkdir(parents=True, exist_ok=True)
        
        # استخراج لینک‌ها
        media_urls = self.extract_media_urls(html_content)
        
        if not media_urls:
            print("⚠️ هیچ فایلی در این پست یافت نشد")
            return [], post_folder
        
        print(f"\n📊 {len(media_urls)} فایل پیدا شد:")
        for i, url in enumerate(media_urls, 1):
            print(f"   {i}. {url.split('/')[-1][:50]}")
        
        # دانلود همزمان فایل‌ها
        downloaded_files = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for idx, media_url in enumerate(media_urls):
                # استخراج نام فایل
                filename = media_url.split('/')[-1].split('?')[0]
                if not filename or '.' not in filename:
                    filename = f"file_{idx+1}.bin"
                
                # پاکسازی نام فایل
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                filepath = post_folder / filename
                
                future = executor.submit(self.download_single_file, media_url, filepath)
                futures[future] = (media_url, filepath)
            
            for future in as_completed(futures):
                media_url, filepath = futures[future]
                if future.result():
                    downloaded_files.append(str(filepath))
        
        # ذخیره متادیتا
        metadata = {
            'channel': channel,
            'post_id': post_id,
            'url': url,
            'download_date': datetime.now().isoformat(),
            'files_count': len(downloaded_files),
            'files': downloaded_files
        }
        
        (post_folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        print(f"\n✨ دانلود کامل شد! {len(downloaded_files)} فایل")
        print(f"📁 مسیر: {post_folder}")
        
        return downloaded_files, post_folder

def main():
    parser = argparse.ArgumentParser(description='Telegram Power Downloader')
    parser.add_argument('--urls', '-u', nargs='+', required=True, help='لینک‌های تلگرام (چندتا با فاصله)')
    parser.add_argument('--output', '-o', default='downloads', help='پوشه خروجی')
    
    args = parser.parse_args()
    
    downloader = TelegramPowerDownloader(args.output)
    
    all_downloads = []
    for url in args.urls:
        print(f"\n📥 پردازش: {url}")
        try:
            files, folder = downloader.download_post(url)
            all_downloads.extend(files)
        except Exception as e:
            print(f"❌ خطا در {url}: {e}")
    
    print(f"\n🎯 مجموع دانلودها: {len(all_downloads)} فایل")

if __name__ == "__main__":
    main()
