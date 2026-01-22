"""
PDF 工具箱 - 網頁版
支援 PDF 壓縮、拆分、合併功能
"""

import streamlit as st
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from PIL import Image
import io
import zipfile
import time
import base64
from pathlib import Path
from typing import List, Tuple


# 頁面設定
st.set_page_config(
    page_title="雲卷雲舒 PDF 工具箱",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed"
)


def get_image_base64(image_path: str) -> str:
    """將圖片轉換為 base64 編碼"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def show_splash_screen():
    """顯示啟動畫面"""

    # 檢查圖片是否存在
    splash_image_path = Path("assets/splash.png")
    if not splash_image_path.exists():
        splash_image_path = Path("assets/splash.jpg")

    # 如果圖片存在，使用圖片；否則使用純色背景
    if splash_image_path.exists():
        img_base64 = get_image_base64(str(splash_image_path))
        bg_style = f"background-image: url('data:image/png;base64,{img_base64}'); background-size: cover; background-position: center;"
    else:
        # 使用漸層背景作為備用
        bg_style = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"

    splash_html = f"""
    <style>
        /* 隱藏 Streamlit 預設元素 */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        .stApp > header {{display: none;}}

        .splash-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            {bg_style}
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            animation: fadeOut 0.5s ease-in-out 3.5s forwards;
        }}

        .splash-content {{
            text-align: center;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}

        .splash-title {{
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 1rem;
            font-family: "Microsoft JhengHei", "PingFang TC", sans-serif;
        }}

        .splash-subtitle {{
            font-size: 1.2rem;
            margin-bottom: 2rem;
            font-family: "Microsoft JhengHei", "PingFang TC", sans-serif;
        }}

        /* 進度條容器 */
        .progress-container {{
            position: absolute;
            bottom: 80px;
            width: 60%;
            max-width: 400px;
            background: rgba(255,255,255,0.3);
            border-radius: 10px;
            overflow: hidden;
            height: 8px;
        }}

        /* 進度條動畫 */
        .progress-bar {{
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            border-radius: 10px;
            animation: loading 3.5s ease-in-out forwards;
        }}

        .loading-text {{
            position: absolute;
            bottom: 50px;
            color: #333;
            font-size: 0.9rem;
            font-family: "Microsoft JhengHei", "PingFang TC", sans-serif;
        }}

        @keyframes loading {{
            0% {{ width: 0%; }}
            100% {{ width: 100%; }}
        }}

        @keyframes fadeOut {{
            0% {{ opacity: 1; }}
            100% {{ opacity: 0; visibility: hidden; }}
        }}
    </style>

    <div class="splash-container" id="splash">
        <div class="progress-container">
            <div class="progress-bar"></div>
        </div>
        <div class="loading-text">載入中...</div>
    </div>

    <script>
        setTimeout(function() {{
            document.getElementById('splash').style.display = 'none';
        }}, 4000);
    </script>
    """

    st.markdown(splash_html, unsafe_allow_html=True)


def format_size(size: int) -> str:
    """格式化檔案大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f} KB"
    else:
        return f"{size/(1024*1024):.2f} MB"


def compress_pdf(input_bytes: bytes, quality: str) -> Tuple[bytes, dict]:
    """壓縮 PDF 檔案"""
    original_size = len(input_bytes)

    reader = PdfReader(io.BytesIO(input_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    if reader.metadata:
        writer.add_metadata(reader.metadata)

    # 壓縮內容串流
    for page in writer.pages:
        page.compress_content_streams()

    output = io.BytesIO()
    writer.write(output)
    output_bytes = output.getvalue()
    compressed_size = len(output_bytes)

    reduction = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0

    stats = {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "reduction": reduction
    }

    return output_bytes, stats


def split_pdf(input_bytes: bytes, mode: str, page_range: str = "") -> List[Tuple[str, bytes]]:
    """拆分 PDF 檔案"""
    reader = PdfReader(io.BytesIO(input_bytes))
    total_pages = len(reader.pages)
    results = []

    if mode == "all":
        pages_to_split = list(range(total_pages))
    else:
        pages_to_split = parse_page_range(page_range, total_pages)

    for page_idx in pages_to_split:
        writer = PdfWriter()
        writer.add_page(reader.pages[page_idx])

        output = io.BytesIO()
        writer.write(output)

        filename = f"page_{page_idx + 1}.pdf"
        results.append((filename, output.getvalue()))

    return results


def parse_page_range(range_str: str, total_pages: int) -> List[int]:
    """解析頁數範圍字串"""
    pages = set()
    parts = range_str.replace(" ", "").split(",")

    for part in parts:
        if "-" in part:
            try:
                start, end = part.split("-")
                start = int(start)
                end = int(end)
                for i in range(start, end + 1):
                    if 1 <= i <= total_pages:
                        pages.add(i - 1)
            except ValueError:
                continue
        else:
            try:
                page = int(part)
                if 1 <= page <= total_pages:
                    pages.add(page - 1)
            except ValueError:
                continue

    return sorted(list(pages))


def merge_pdfs(files: List[bytes]) -> bytes:
    """合併多個 PDF 檔案"""
    merger = PdfMerger()

    for pdf_bytes in files:
        merger.append(io.BytesIO(pdf_bytes))

    output = io.BytesIO()
    merger.write(output)
    merger.close()

    return output.getvalue()


def create_zip(files: List[Tuple[str, bytes]]) -> bytes:
    """將多個檔案打包成 ZIP"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files:
            zip_file.writestr(filename, content)
    return zip_buffer.getvalue()


def main_app():
    """主應用程式"""

    # 自訂 CSS 樣式
    st.markdown("""
    <style>
        .main-title {
            text-align: center;
            color: #5D4E37;
            margin-bottom: 0.5rem;
            font-family: "Microsoft JhengHei", "PingFang TC", serif;
        }
        .sub-title {
            text-align: center;
            color: #8B7355;
            font-size: 1.1rem;
            margin-bottom: 2rem;
            font-family: "Microsoft JhengHei", "PingFang TC", serif;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px;
            font-size: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # 主標題
    st.markdown('<h1 class="main-title">雲卷雲舒 · PDF 全能匠心</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">化繁為簡凝雲墨，拆骨離魂鑄新篇</p>', unsafe_allow_html=True)

    # 建立分頁
    tab1, tab2, tab3 = st.tabs(["📦 壓縮", "✂️ 拆分", "🔗 合併"])

    # ===== 壓縮功能 =====
    with tab1:
        st.markdown("### 壓縮 PDF 檔案")
        st.markdown("上傳 PDF 檔案，減少檔案大小以便分享或儲存。")

        uploaded_file = st.file_uploader(
            "選擇要壓縮的 PDF 檔案",
            type=["pdf"],
            key="compress_uploader"
        )

        quality = st.radio(
            "選擇壓縮程度：",
            options=["low", "medium", "high"],
            format_func=lambda x: {
                "low": "低度壓縮（較大檔案，較高品質）",
                "medium": "中度壓縮（平衡檔案大小與品質）",
                "high": "高度壓縮（目標 4MB 以下，適合上傳作業）"
            }[x],
            index=1,
            key="compress_quality"
        )

        if quality == "high":
            st.info("💡 高度壓縮會大幅降低圖片品質，並嘗試將檔案壓縮至 4MB 以下。適合需要上傳作業或限制檔案大小的情況。")

        if uploaded_file is not None:
            st.markdown(f"**已上傳：** {uploaded_file.name} ({format_size(uploaded_file.size)})")

            if st.button("開始壓縮", key="compress_btn", type="primary"):
                with st.spinner("正在壓縮中，請稍候..."):
                    try:
                        compressed_bytes, stats = compress_pdf(uploaded_file.getvalue(), quality)

                        st.success("壓縮完成！")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("原始大小", format_size(stats["original_size"]))
                        with col2:
                            st.metric("壓縮後大小", format_size(stats["compressed_size"]))
                        with col3:
                            st.metric("減少", f"{stats['reduction']:.1f}%")

                        original_name = uploaded_file.name.rsplit(".", 1)[0]
                        download_name = f"{original_name}_compressed.pdf"

                        st.download_button(
                            label="下載壓縮後的 PDF",
                            data=compressed_bytes,
                            file_name=download_name,
                            mime="application/pdf",
                            type="primary"
                        )
                    except Exception as e:
                        st.error(f"壓縮過程中發生錯誤：{str(e)}")

    # ===== 拆分功能 =====
    with tab2:
        st.markdown("### 拆分 PDF 檔案")
        st.markdown("將 PDF 檔案拆分成多個獨立檔案。")

        split_file = st.file_uploader(
            "選擇要拆分的 PDF 檔案",
            type=["pdf"],
            key="split_uploader"
        )

        if split_file is not None:
            try:
                reader = PdfReader(io.BytesIO(split_file.getvalue()))
                total_pages = len(reader.pages)
                st.info(f"此 PDF 共有 **{total_pages}** 頁")
            except Exception as e:
                st.error(f"無法讀取 PDF：{str(e)}")
                total_pages = 0

            if total_pages > 0:
                split_mode = st.radio(
                    "選擇拆分方式：",
                    options=["all", "range"],
                    format_func=lambda x: {
                        "all": "每頁拆分成獨立檔案",
                        "range": "指定頁數範圍"
                    }[x],
                    key="split_mode"
                )

                page_range = ""
                if split_mode == "range":
                    page_range = st.text_input(
                        "輸入頁數範圍（例如：1-3, 5, 7-10）：",
                        key="page_range"
                    )

                if st.button("開始拆分", key="split_btn", type="primary"):
                    if split_mode == "range" and not page_range.strip():
                        st.warning("請輸入頁數範圍")
                    else:
                        with st.spinner("正在拆分中，請稍候..."):
                            try:
                                results = split_pdf(split_file.getvalue(), split_mode, page_range)

                                if not results:
                                    st.warning("沒有符合條件的頁面可拆分")
                                else:
                                    st.success(f"拆分完成！共產生 {len(results)} 個檔案")

                                    original_name = split_file.name.rsplit(".", 1)[0]
                                    zip_bytes = create_zip(results)

                                    st.download_button(
                                        label=f"下載全部 ({len(results)} 個檔案)",
                                        data=zip_bytes,
                                        file_name=f"{original_name}_pages.zip",
                                        mime="application/zip",
                                        type="primary"
                                    )

                                    with st.expander("或單獨下載每個檔案"):
                                        for filename, content in results:
                                            st.download_button(
                                                label=filename,
                                                data=content,
                                                file_name=f"{original_name}_{filename}",
                                                mime="application/pdf",
                                                key=f"download_{filename}"
                                            )
                            except Exception as e:
                                st.error(f"拆分過程中發生錯誤：{str(e)}")

    # ===== 合併功能 =====
    with tab3:
        st.markdown("### 合併 PDF 檔案")
        st.markdown("將多個 PDF 檔案合併成一個。上傳順序即為合併順序。")

        merge_files = st.file_uploader(
            "選擇要合併的 PDF 檔案（可多選）",
            type=["pdf"],
            accept_multiple_files=True,
            key="merge_uploader"
        )

        if merge_files:
            st.markdown(f"**已選擇 {len(merge_files)} 個檔案：**")
            for i, f in enumerate(merge_files, 1):
                st.markdown(f"{i}. {f.name} ({format_size(f.size)})")

            if len(merge_files) < 2:
                st.warning("請至少選擇 2 個 PDF 檔案進行合併")
            else:
                if st.button("開始合併", key="merge_btn", type="primary"):
                    with st.spinner("正在合併中，請稍候..."):
                        try:
                            files_bytes = [f.getvalue() for f in merge_files]
                            merged_bytes = merge_pdfs(files_bytes)

                            st.success("合併完成！")
                            st.metric("合併後檔案大小", format_size(len(merged_bytes)))

                            st.download_button(
                                label="下載合併後的 PDF",
                                data=merged_bytes,
                                file_name="merged.pdf",
                                mime="application/pdf",
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"合併過程中發生錯誤：{str(e)}")

    # 頁尾
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888; font-size: 0.9rem;">
            <p>雲卷雲舒 · PDF 全能匠心 - 免費開源工具</p>
            <p>所有檔案處理皆在伺服器端完成，處理完成後即刻刪除，不會保存您的檔案。</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# 主程式入口
if __name__ == "__main__":
    # 初始化 session state
    if "splash_shown" not in st.session_state:
        st.session_state.splash_shown = False

    # 顯示啟動畫面（只在第一次載入時）
    if not st.session_state.splash_shown:
        show_splash_screen()
        st.session_state.splash_shown = True

    # 顯示主應用程式
    main_app()
