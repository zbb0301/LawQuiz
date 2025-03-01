# LawQuiz

法律考試題目處理系統，用於處理並轉換各類公務人員考試的題目資料。

## 專案結構

```
.
├── data/                    # 原始資料目錄
│   ├── *.pdf               # PDF格式的考試題目
│   └── ExamQandA_Csv.csv   # 考選部網站下載的CSV格式考試題目
├── output/                  # 輸出資料目錄
│   └── 101/                # 按年份和考試類型組織的題目
├── src/                     # 源代碼目錄
│   ├── csv_processor.py    # CSV檔案處理模組
│   └── pdf_processor.py    # PDF檔案處理模組
└── requirements.txt        # Python套件依賴清單
```

## 功能特點

- 支援PDF格式考試題目的解析和轉換
- 支援CSV格式考試題目的處理
- 將題目轉換為標準化的JSON格式
- 按照年份和考試類型組織題目資料

## 資料格式

處理後的JSON格式包含以下資訊：
- 考試基本資訊（考試名稱、等別、類別、科目）
- 試題內容（題號、問題、答案）

## 系統需求

- Python 3.x
- 主要依賴套件：
  - pdfplumber 0.10.2 - PDF文件處理
  - pandas 2.1.1 - CSV數據處理
  - requests 2.31.0 - HTTP請求處理

## 安裝

1. 克隆此專案：
```bash
git clone https://github.com/zbb0301/LawQuiz.git
cd LawQuiz
```

2. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

## 使用方法

### PDF處理
使用 pdf_processor.py 處理PDF格式的考試題目與答案：
```bash
python src/pdf_processor.py 題目檔案.pdf 答案檔案.pdf [-o 輸出檔案.json]
```

參數說明：
- 題目檔案.pdf：考試題目的PDF檔案
- 答案檔案.pdf：考試答案的PDF檔案
- -o, --output：(選填) 指定輸出的JSON檔案路徑，預設為 output/quiz_qa.json

範例：
```bash
python src/pdf_processor.py data/101040_4201.pdf data/101040_ANS4201.pdf
```

### CSV處理
使用 csv_processor.py 處理從考選部網站下載的考試題目CSV檔案：
```bash
python src/csv_processor.py data/ExamQandA_Csv.csv
```

處理後的檔案將輸出至 output 目錄，並按照年份和考試類型進行分類。題目資料會被轉換成標準化格式，方便後續使用和整理。