#!/usr/bin/env python3
"""
Telegram Power Downloader - نسخه نهایی با Debug کامل
"""

import os
import re
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import time

class TelegramDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
    def extract_post_info(self, url):
        """استخراج اطلاعات پست"""
        patterns = [
            r't\.me/([^/]+)/(\d+)',
            r'telegram\.me/([^/]+)/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        raise ValueError(f"لینک نامعتبر: {url}")
    
    def get_page_content(self, channel, post_id):
        """دریافت محتوای صفحه با روش‌های مختلف"""
        methods = [
            # روش اول: صفحه عادی
            f"https://t.me/{channel}/{post_id}",
            # روش دوم: با embed
            f"https://t.me/{channel}/{post_id}?embed=1",
            # روش سوم: نسخه ساده
            f"https://t.me/s/{channel}/{post_id}",
        ]
        
        for url in methods:
            try:
                print(f"🔄 تلاش: {url}")
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    print(f"✅ موفق: {url}")
                    return resp.text
            except:
                continue
        
        raise Exception("همه روش‌ها ناموفق بودن")
    
    def save_debug_info(self, folder, html_content, url):
        """ذخیره اطلاعات دیباگ برای بررسی"""
        debug_folder = folder / "_debug"
        debug_folder.mkdir(exist_ok=True)
        
        # ذخیره HTML صفحه
        (debug_folder / "page.html").write_text(html_content, encoding='utf-8')
        
        # ذخیره لینک اصلی
        (debug_folder / "url.txt").write_text(url, encoding='utf-8')
        
        # جستجوی الگوهای مختلف در HTML
        patterns_found = {}
        
        patterns_to_check = {
            'video_links': r'href="([^"]*\.(mp4|mkv|avi|mov))"',
            'audio_links': r'href="([^"]*\.(mp3|ogg|m4a|wav))"',
            'image_links': r'src="([^"]*\.(jpg|jpeg|png|gif|webp))"',
            'file_links': r'href="([^"]*\.(pdf|zip|rar|exe|apk|doc|xls))"',
            'telegram_files': r'href="(/file/[^"]+)"',
            'tg_media': r'src="(https://[^"]*cdn[^"]*telegram[^"]+)"',
            'data_attributes': r'data-(?:file|document|video)-url="([^"]+)"',
        }
        
        for name, pattern in patterns_to_check.items():
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                patterns_found[name] = matches[:5]  # فقط 5 تا اول
        
        # ذخیره نتایج جستجو
        (debug_folder / "patterns_found.json").write_text(
            json.dumps(patterns_found, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        return patterns_found
    
    def extract_all_urls(self, html_content):
        """استخراج تمام URLهای ممکن"""
        all_urls = []
        
        # الگوهای مختلف
        patterns = [
            # فایل‌های مستقیم
            r'(?:href|src)=["\']([^"\']+\.(?:mp4|mp3|jpg|jpeg|png|gif|pdf|zip|rar|7z|exe|apk|doc|docx|xls|xlsx|ppt|pptx))["\']',
            # فایل‌های تلگرام
            r'(?:href|src)=["\'](/file/[^"\']+)["\']',
            # آدرس‌های cdn تلگرام
            r'(?:href|src)=["\'](https://[^"\']*cdn[^"\']*telegram[^"\']+)["\']',
            # دیتا اتریبیوت‌ها
            r'data-(?:file|document|video|audio)-url=["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                url = match if isinstance(match, str) else match[0]
                # تکمیل URLهای نسبی
                if url.startswith('/file/'):
                    url = f"https://t.me{url}"
                elif url.startswith('/'):
                    url = f"https://t.me{url}"
                elif url.startswith('//'):
                    url = f"https:{url}"
                
                if url.startswith('http') and url not in all_urls:
                    all_urls.append(url)
        
        return all_urls
    
    def download_post(self, url):
        """دانلود پست تلگرام با ذخیره کامل اطلاعات"""
        print("\n" + "="*70)
        print("🚀 Telegram Downloader - Version 2.0")
        print("="*70)
        
        # استخراج اطلاعات
        try:
            channel, post_id = self.extract_post_info(url)
            print(f"📺 کانال: @{channel}")
            print(f"🆔 شناسه پست: {post_id}")
        except Exception as e:
            print(f"❌ خطا: {e}")
            return False
        
        # ایجاد پوشه اصلی
        post_folder = self.output_dir / f"{channel}_{post_id}"
        post_folder.mkdir(parents=True, exist_ok=True)
        print(f"📁 پوشه ساخته شد: {post_folder}")
        
        # دریافت محتوا
        try:
            html_content = self.get_page_content(channel, post_id)
            print(f"📄 حجم صفحه: {len(html_content):,} کاراکتر")
        except Exception as e:
            print(f"❌ خطا در دریافت صفحه: {e}")
            self.save_debug_info(post_folder, f"Error: {e}", url)
            return False
        
        # ذخیره HTML برای دیباگ
        (post_folder / "page_source.html").write_text(html_content, encoding='utf-8')
        
        # استخراج متن پست
        text_content = ""
        text_patterns = [
            r'<div class="tgme_widget_message_text"[^>]*>(.*?)</div>',
            r'<div class="message-text"[^>]*>(.*?)</div>',
            r'<meta property="og:description" content="([^"]+)"',
        ]
        
        for pattern in text_patterns:
            match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
            if match:
                text_content = match.group(1)
                text_content = re.sub(r'<[^>]+>', '', text_content)
                text_content = re.sub(r'&[a-z]+;', '', text_content)
                break
        
        if text_content:
            text_file = post_folder / "message.txt"
            text_file.write_text(text_content, encoding='utf-8')
            print(f"📝 متن پست ذخیره شد ({len(text_content)} کاراکتر)")
        else:
            print("ℹ️ متنی در این پست وجود ندارد")
        
        # استخراج همه URLها
        all_urls = self.extract_all_urls(html_content)
        
        # ذخیره اطلاعات دیباگ و جستجوی پیشرفته
        patterns_found = self.save_debug_info(post_folder, html_content, url)
        
        # گزارش نتایج جستجو
        print("\n🔍 نتایج جستجو:")
        has_any = False
        for name, items in patterns_found.items():
            if items:
                print(f"   ✅ {name}: {len(items)} مورد پیدا شد")
                has_any = True
            else:
                print(f"   ❌ {name}: پیدا نشد")
        
        # دانلود فایل‌ها
        if all_urls:
            print(f"\n📊 {len(all_urls)} فایل پیدا شد:")
            downloaded = 0
            for idx, file_url in enumerate(all_urls, 1):
                filename = file_url.split('/')[-1].split('?')[0]
                if not filename or '.' not in filename:
                    filename = f"file_{idx}.bin"
                
                # پاکسازی نام فایل
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                filepath = post_folder / filename
                
                print(f"   {idx}. {filename[:50]}")
                
                # تلاش برای دانلود
                try:
                    resp = self.session.get(file_url, stream=True, timeout=30)
                    if resp.status_code == 200:
                        with open(filepath, 'wb') as f:
                            for chunk in resp.iter_content(8192):
                                if chunk:
                                    f.write(chunk)
                        print(f"      ✅ دانلود شد ({filepath.stat().st_size:,} bytes)")
                        downloaded += 1
                    else:
                        print(f"      ⚠️ خطا: HTTP {resp.status_code}")
                except Exception as e:
                    print(f"      ❌ خطا: {str(e)[:50]}")
        else:
            print("\n⚠️ هیچ فایل قابل دانلودی پیدا نشد!")
            print("\n💡 دلایل احتمالی:")
            print("   1️⃣ این پست فقط متن دارد و فایل ضمیمه ندارد")
            print("   2️⃣ فایل در ویجت جاسازی شده (مثل یوتیوب) است")
            print("   3️⃣ پست خصوصی یا حذف شده است")
            print(f"\n📁 اطلاعات دیباگ در پوشه {post_folder}/_debug ذخیره شد")
            print("   فایل page.html را باز کنید تا محتوای واقعی صفحه را ببینید")
        
        # ذخیره متادیتا
        metadata = {
            'channel': channel,
            'post_id': post_id,
            'url': url,
            'download_date': datetime.now().isoformat(),
            'has_text': bool(text_content),
            'files_found': len(all_urls),
            'files_downloaded': downloaded if 'downloaded' in locals() else 0,
            'debug_info': {
                'patterns_found': {k: len(v) for k, v in patterns_found.items()},
                'html_size': len(html_content)
            }
        }
        
        (post_folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        print("\n" + "="*70)
        print(f"✨ عملیات کامل شد!")
        print(f"📁 مسیر: {post_folder}")
        print("="*70)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Telegram Downloader')
    parser.add_argument('--url', '-u', required=True, help='لینک پست تلگرام')
    parser.add_argument('--output', '-o', default='downloads', help='پوشه خروجی')
    
    args = parser.parse_args()
    
    downloader = TelegramDownloader(args.output)
    success = downloader.download_post(args.url)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
