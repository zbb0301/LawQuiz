import os
import csv
import requests
import json
from itertools import islice
from pdf_processor import PDFQuizProcessor
import re

def download_exam_csv():
    """從考選部網站下載考試題庫CSV檔案"""
    url = "https://wwwc.moex.gov.tw/main/Exam/wHandExamQandA_CSV.ashx"
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # 確保data目錄存在
        os.makedirs('data', exist_ok=True)
        csv_path = os.path.join('data', 'ExamQandA_Csv.csv')
        
        # 將內容寫入檔案
        with open(csv_path, 'wb') as f:
            f.write(response.content)
        return csv_path
    except Exception as e:
        print(f"下載考試題庫CSV失敗: {str(e)}")
        return None

def generate_safe_filename(url, is_question=True):
    """從 URL 生成安全的檔案名稱"""
    # 提取查詢參數
    params = dict(param.split('=') for param in url.split('?')[1].split('&'))
    # 生成格式：code_c_s_q_Q.pdf 或 code_c_s_q_A.pdf
    suffix = '_Q' if is_question else '_A'
    return f"{params['code']}_{params['c']}_{params['s']}_{params['q']}{suffix}.pdf"

def process_csv(sample_size=100):
    print(f"開始處理，只取司法人員考試前 {sample_size} 筆資料...")
    
    # 從考選部網站下載最新的CSV檔案
    csv_path = download_exam_csv()
    if not csv_path:
        print("無法取得考試題庫CSV檔案，程序終止")
        return
        
    output_base = 'output'
    
    processed_count = 0
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 篩選司法人員考試
            if not "法學" in row['科目全名']:
                continue
                
            # 檢查是否已達到指定筆數
            if processed_count >= sample_size:
                break
                
            exam_code = row['考試代碼']
            exam_name = row['考試名稱']
            print(f"處理第 {exam_code} 考試代碼: {exam_name}...")
            
            # 建立目錄結構
            path_parts = [
                row['考試年度'],
                exam_code,
                exam_name,
                row['等級代碼'],
                row['等級分類'],
                row['考試及等別'],
                row['類科代碼'],
                row['類科組別']
            ]
            
            current_path = output_base
            for part in path_parts:
                if part:  # 只有當part不是空的時候才建立
                    current_path = os.path.join(current_path, str(part))
                    os.makedirs(current_path, exist_ok=True)
            
            # 下載試題和答案的PDF
            question_url = row['試題網址']
            answer_url = row['測驗式試題答案網址']
            
            if question_url and answer_url:
                # 生成更安全的檔案名稱，分別加上 _Q 和 _A
                q_filename = generate_safe_filename(question_url, True)
                a_filename = generate_safe_filename(answer_url, False)
                q_path = os.path.join(current_path, q_filename)
                a_path = os.path.join(current_path, a_filename)
                
                print(f"下載試題: {q_filename}")
                download_pdf(question_url, q_path)
                
                print(f"下載答案: {a_filename}")
                download_pdf(answer_url, a_path)
                
                # 建立 PDFQuizProcessor 實例並處理 PDF
                print(f"處理 PDF 並產生 JSON...")
                processor = PDFQuizProcessor(q_path, a_path)
                output_json = os.path.join(current_path, f"{os.path.splitext(q_filename)[0]}_qa.json")
                try:
                    processor.process_and_save(output_json)
                    print(f"已完成 {q_filename} 的處理\n")
                except Exception as e:
                    print(f"處理 PDF 時發生錯誤: {str(e)}\n")
            
            processed_count += 1

def download_pdf(url, save_path):
    """下載PDF檔案"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        print(f"下載 {url} 失敗: {str(e)}")

if __name__ == '__main__':
    process_csv()