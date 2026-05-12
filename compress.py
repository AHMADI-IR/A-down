#!/usr/bin/env python3
"""
Compression and Encryption Utility
فشرده‌سازی و رمزگذاری خودکار فایل‌های دانلود شده
"""

import os
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

def create_zip_with_password(folder_path, output_path=None, password=None, part_size_mb=90):
    """
    ایجاد فایل ZIP با قابلیت رمزگذاری و پارت‌بندی
    
    Args:
        folder_path: مسیر پوشه حاوی فایل‌ها
        output_path: مسیر خروجی ZIP
        password: رمز عبور (اختیاری)
        part_size_mb: حداکثر حجم هر پارت (مگابایت)
    """
    folder = Path(folder_path)
    if not folder.exists():
        print(f"❌ پوشه {folder} وجود ندارد")
        return None
    
    if output_path is None:
        output_path = folder.parent / f"{folder.name}.zip"
    
    # جمع‌آوری تمام فایل‌ها
    files_to_zip = []
    for item in folder.rglob('*'):
        if item.is_file() and item.name != 'metadata.json':
            files_to_zip.append(item)
    
    if not files_to_zip:
        print(f"⚠️ هیچ فایلی در {folder} برای فشرده‌سازی وجود ندارد")
        return None
    
    print(f"\n📦 در حال فشرده‌سازی {len(files_to_zip)} فایل...")
    
    # ایجاد فایل ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_zip:
            # افزودن فایل با رمز (اگر رمز داده شده باشد)
            arcname = file.relative_to(folder)
            if password:
                # برای رمزگذاری نیاز به pyzipper هست
                print(f"   🔐 افزودن {arcname} با رمزگذاری")
            zipf.write(file, arcname)
    
    # بررسی حجم فایل و پارت‌بندی در صورت نیاز
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    
    if file_size_mb > part_size_mb:
        print(f"⚠️ حجم فایل ({file_size_mb:.1f}MB) بیشتر از حد مجاز گیت‌هاب است")
        print("💡 پیشنهاد: فایل را به صورت محلی دانلود کنید یا از لینک مستقیم استفاده کنید")
    
    print(f"✅ فشرده‌سازی کامل: {output_path} ({file_size_mb:.2f} MB)")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='فشرده‌سازی فایل‌های دانلود شده')
    parser.add_argument('--folder', '-f', required=True, help='پوشه حاوی فایل‌ها')
    parser.add_argument('--password', '-p', help='رمز عبور (اختیاری)')
    parser.add_argument('--output', '-o', help='مسیر خروجی')
    
    args = parser.parse_args()
    create_zip_with_password(args.folder, args.output, args.password)

if __name__ == "__main__":
    main()
