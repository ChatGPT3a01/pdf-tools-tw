# PDF 工具箱 (PDF Tools TW)

免費線上 PDF 壓縮、拆分、合併工具。繁體中文介面，簡單易用。

## 功能特色

### 📦 PDF 壓縮
- 上傳 PDF 檔案，自動壓縮減少檔案大小
- 三種壓縮程度可選：低度、中度、高度
- 即時顯示壓縮前後檔案大小比較

### ✂️ PDF 拆分
- 將 PDF 每頁拆分成獨立檔案
- 支援指定頁數範圍（如：1-3, 5, 7-10）
- 自動打包成 ZIP 方便下載

### 🔗 PDF 合併
- 上傳多個 PDF 檔案合併成一個
- 依照上傳順序進行合併
- 支援拖放上傳

## 線上使用

直接訪問：**[PDF 工具箱](https://pdf-tools-tw.streamlit.app)**

## 本地安裝

### 需求
- Python 3.8 或以上版本

### 安裝步驟

1. 複製專案
```bash
git clone https://github.com/YOUR_USERNAME/pdf-tools-tw.git
cd pdf-tools-tw
```

2. 安裝依賴套件
```bash
pip install -r requirements.txt
```

3. 執行程式
```bash
streamlit run app.py
```

4. 開啟瀏覽器訪問 `http://localhost:8501`

## 部署到 Streamlit Cloud

1. 將專案推送到 GitHub
2. 前往 [Streamlit Cloud](https://share.streamlit.io/)
3. 點擊「New app」
4. 選擇你的 GitHub 儲存庫
5. 設定主檔案為 `app.py`
6. 點擊「Deploy」

## 隱私說明

- 所有檔案處理皆在伺服器端完成
- 處理完成後檔案即刻刪除
- 不會保存或分享您的檔案

## 技術棧

- [Streamlit](https://streamlit.io/) - 網頁框架
- [pypdf](https://github.com/py-pdf/pypdf) - PDF 處理庫
- Python 3.8+

## 授權

MIT License

## 貢獻

歡迎提交 Issue 或 Pull Request！
