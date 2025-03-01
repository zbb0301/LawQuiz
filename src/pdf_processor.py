import pdfplumber
import pandas as pd
import os
import re
from pathlib import Path
import logging
import pytesseract
import json

# 設定日誌記錄
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFQuizProcessor:
    def __init__(self, questions_pdf, answers_pdf):
        self.questions_pdf = questions_pdf
        self.answers_pdf = answers_pdf

    def extract_text_from_pdf(self, pdf_path):
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    page_text = self.validate_text_chars(page_text)
                    text += page_text or ""
            return text
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

    def _clean_exam_info(self, exam_text):
        # 移除代號、頁次、考試時間等不必要資訊
        exam_text = re.sub(r"代號：\S+", "", exam_text)
        exam_text = re.sub(r"頁次：\S+", "", exam_text)
        exam_text = re.sub(r"考試時間：\s*\S+\s*\S+", "", exam_text)
        # 移除「座號：」及其後所有內容
        exam_text = re.split(r"座號：", exam_text)[0]
        return exam_text.strip()

    def extract_header_info(self, text):
        """
        從完整文字中分離頁首 header 資訊與題目部分
        頁首會包含「等別」、「類（科）別」與「科目」，其它部分當作考試資訊
        """
        lines = text.splitlines()
        header_lines = []
        body_lines = []
        start_body = False
        # 當遇到符合題目開頭的行（數字加空白後非數字）時，視為題目開始
        for line in lines:
            if not start_body and re.match(r'^\d+\s+[^\d]', line):
                start_body = True
            if not start_body:
                header_lines.append(line)
            else:
                body_lines.append(line)
        header_info = {"考試": "", "等別": "", "類別": "", "科目": ""}
        exam_parts = []
        for line in header_lines:
            m = re.search(r"等\s*別[:：]\s*(.+)", line)
            if m:
                header_info["等別"] = m.group(1).strip()
                continue
            m = re.search(r"類（科）別[:：]\s*(.+)", line)
            if m:
                header_info["類別"] = m.group(1).strip()
                continue
            m = re.search(r"科\s*目[:：]\s*(.+)", line)
            if m:
                header_info["科目"] = m.group(1).strip()
                continue
            if line.strip():
                exam_parts.append(line.strip())
        header_info["考試"] = self._clean_exam_info(" ".join(exam_parts))
        return header_info, "\n".join(body_lines)

    def process_questions(self, questions_text):
        questions = []
        lines = re.split(r'\r\n|\n|\r', questions_text)
        current_question = ""
        start_processing = False

        def has_all_options(text):
            # 檢查是否同時含有 (A)、(B)、(C) 與 (D)
            return all(opt in text for opt in ["(A)", "(B)", "(C)", "(D)"])

        for line in lines:
            line = line.strip()
            # 若尚未開始累積題目，遇到數字開頭就啟動
            if not start_processing and re.match(r'^\d+\s', line):
                start_processing = True

            if start_processing:
                # 如果當前行看似為新題的開頭（數字開頭）且目前的題目內容已完整
                if re.match(r'^\d+\s', line) and current_question and has_all_options(current_question):
                    questions.append(current_question.strip())
                    current_question = line  # 以本行重新開始累積下一題
                else:
                    # 沒達成完全的選項條件則累積至同一題
                    if current_question:
                        current_question += " " + line
                    else:
                        current_question = line

        if current_question:
            questions.append(current_question.strip())

        return questions

    def process_answers(self, answers_text):
        answers_dict = {}
        lines = answers_text.split('\n')

        for i, line in enumerate(lines):
            if '題號' in line:
                question_numbers = line.replace('題號', '').strip().split()
                if i + 1 < len(lines) and '答案' in lines[i + 1]:
                    answers_line = lines[i + 1].replace('答案', '').strip().split()
                    for qn, ans in zip(question_numbers, answers_line):
                        if qn.isdigit():
                            num = int(qn)
                            answers_dict[num] = ans

        return answers_dict

    def validate_text_chars(self, text):
        """
        檢查 text 中每個字元是否屬於允許的 Unicode 範圍，如果不是則替換為特定字串
        """
        special_chars = {
            57740: "(A)",
            57741: "(B)",
            57742: "(C)",
            57743: "(D)",
            8251: "※",
            57641: "(一)",
            57642: "(二)",
            57643: "(三)",
        }

        def is_valid_char(c):
            cp = ord(c)
            ranges = [
                # 【拉丁字母與基本符號】
                (0x0000, 0x007F),   # Basic Latin
                (0x0080, 0x00FF),   # Latin-1 Supplement
                (0x0100, 0x017F),   # Latin Extended-A
                (0x0180, 0x024F),   # Latin Extended-B
                (0x1E00, 0x1EFF),   # Latin Extended Additional

                # 【常見標點與符號】
                (0x2000, 0x206F),   # General Punctuation
                (0x20A0, 0x20CF),   # Currency Symbols
                (0x2100, 0x214F),   # Letterlike Symbols
                (0x2150, 0x218F),   # Number Forms
                (0x2190, 0x21FF),   # Arrows
                (0x2200, 0x22FF),   # Mathematical Operators
                (0x2300, 0x23FF),   # Miscellaneous Technical
                (0x2460, 0x24FF),   # Enclosed Alphanumerics
                (0x25A0, 0x25FF),   # Geometric Shapes
                (0x2600, 0x26FF),   # Miscellaneous Symbols
                (0x2700, 0x27BF),   # Dingbats
                (0x27F0, 0x27FF),   # Supplemental Arrows-A
                (0x2900, 0x297F),   # Supplemental Arrows-B
                (0x2980, 0x29FF),   # Miscellaneous Mathematical Symbols-B

                # 【東亞語系基礎區】
                (0x1100, 0x11FF),   # Hangul Jamo
                (0x3040, 0x309F),   # Hiragana
                (0x30A0, 0x30FF),   # Katakana
                (0x31F0, 0x31FF),   # Katakana Phonetic Extensions
                (0xFF65, 0xFF9F),   # Halfwidth Katakana
                (0x3000, 0x303F),   # CJK Symbols and Punctuation

                # 【漢字及其延伸區】
                (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
                (0x4E00, 0x9FFF),   # CJK Unified Ideographs
                (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
                (0x20000, 0x2A6DF), # CJK Unified Ideographs Extension B
                (0x2A700, 0x2B73F), # CJK Unified Ideographs Extension C
                (0x2B740, 0x2B81F), # CJK Unified Ideographs Extension D
                (0x2B820, 0x2CEAF), # CJK Unified Ideographs Extension E
                (0x2CEB0, 0x2EBEF), # CJK Unified Ideographs Extension F
                (0x30000, 0x3134F), # CJK Unified Ideographs Extension G

                # 【韓文字】
                (0xA960, 0xA97F),   # Hangul Jamo Extended-A
                (0xAC00, 0xD7AF),   # Hangul Syllables
                (0xD7B0, 0xD7FF),   # Hangul Jamo Extended-B

                # 【Emoji 及其他圖形符號】（可依需求納入）
                (0x1F300, 0x1F5FF), # Miscellaneous Symbols and Pictographs
                (0x1F600, 0x1F64F), # Emoticons
                (0x1F680, 0x1F6FF), # Transport and Map Symbols
                (0x1F900, 0x1F9FF), # Supplemental Symbols and Pictographs
                (0xFF00, 0xFFEF),   # Fullwidth Forms
            ]

            for start, end in ranges:
                if start <= cp <= end:
                    return True
            return False

        result = []
        for index, c in enumerate(text):
            if is_valid_char(c):
                result.append(c)
            else:
                char_code = ord(c)
                if char_code in special_chars:
                    result.append(special_chars[char_code])
                else:
                    error_msg = f"無法辨識與替換的字元: {c}, {char_code} at index {index}, 前5個字: {text[index - 5:index]}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        return ''.join(result)

    def process_and_save(self, output_file):
        try:
            # 提取問題文字
            questions_text_full = self.extract_text_from_pdf(self.questions_pdf)
            # 從完整文字中分離出 header 資訊與題目部分
            header_info, questions_text = self.extract_header_info(questions_text_full)
            questions = self.process_questions(questions_text)
            answers_text = self.extract_text_from_pdf(self.answers_pdf)
            answers_dict = self.process_answers(answers_text)

            # 解析問題內容，建立題號與問題對應字典
            question_dict = {}
            for q in questions:
                match = re.match(r'(\d+)\s+(.*)', q)
                if match:
                    num = int(match.group(1))
                    question_dict[num] = match.group(2)

            if len(question_dict) != len(answers_dict):
                logger.warning(f"問題數 ({len(question_dict)}) 與答案數 ({len(answers_dict)}) 不一致")

            # 僅取兩邊皆有的題號
            common_numbers = sorted(set(question_dict.keys()) & set(answers_dict.keys()))
            exam_name = Path(self.questions_pdf).stem

            # 輸出 JSON 格式，包含 header 與題目資訊
            output_data = {
                exam_name: {
                    "考試": header_info.get("考試", ""),
                    "等別": header_info.get("等別", ""),
                    "類別": header_info.get("類別", ""),
                    "科目": header_info.get("科目", ""),
                    "題目": [
                        {
                            "題號": num,
                            "問題": question_dict[num],
                            "答案": answers_dict[num]
                        } for num in common_numbers
                    ]
                }
            }

            output_dir = os.path.dirname(output_file)
            os.makedirs(output_dir, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            logger.info(f"已儲存考卷資料到 {output_file}")
        except Exception as e:
            logger.error(f"處理過程中發生錯誤: {str(e)}")
            raise

if __name__ == "__main__":
    import argparse
    
    # 設定命令列參數解析
    parser = argparse.ArgumentParser(description='處理考試題目的 PDF 檔案')
    parser.add_argument('questions_pdf', help='題目PDF檔案路徑')
    parser.add_argument('answers_pdf', help='答案PDF檔案路徑')
    parser.add_argument('-o', '--output', help='輸出的JSON檔案路徑 (選填)')
    
    args = parser.parse_args()
    
    # 設定輸出檔案路徑
    if args.output:
        output_file = Path(args.output)
    else:
        # 如果沒有指定輸出路徑，使用預設路徑
        base_dir = Path(__file__).parent.parent
        output_file = base_dir / "output" / "quiz_qa.json"
    
    # 確保輸出目錄存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 處理PDF
    try:
        processor = PDFQuizProcessor(args.questions_pdf, args.answers_pdf)
        processor.process_and_save(output_file)
        print(f"處理完成！輸出檔案：{output_file}")
    except Exception as e:
        print(f"處理過程發生錯誤：{str(e)}")
        exit(1)