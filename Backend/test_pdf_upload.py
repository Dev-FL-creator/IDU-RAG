#!/usr/bin/env python3
"""测试PDF上传API"""
import requests
import os

def test_pdf_upload():
    # 使用一个测试PDF文件
    test_pdf_path = r"C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\Test Data\Institute VB\ACC Projects\CETSOL.pdf"
    
    if not os.path.exists(test_pdf_path):
        print(f"测试文件不存在: {test_pdf_path}")
        return
    
    # 准备上传数据
    url = "http://localhost:8001/api/extract_pdf_preview"
    
    with open(test_pdf_path, 'rb') as f:
        files = {'files': ('CETSOL.pdf', f, 'application/pdf')}
        data = {
            'chat_model': 'deepseek-chat',
            'pdf_extraction_method': 'pymupdf',  # 先使用pymupdf测试
            'pdf_extraction_fallback': 'true'
        }
        
        try:
            response = requests.post(url, files=files, data=data)
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")
        except Exception as e:
            print(f"请求失败: {e}")

if __name__ == "__main__":
    test_pdf_upload()