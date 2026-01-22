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


def compress_image(image_data: bytes, quality: int) -> bytes:
    """壓縮單張圖片"""
    try:
        img = Image.open(io.BytesIO(image_data))

        # 轉換為 RGB（如果是 RGBA 或其他模式）
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' or img.mode == 'LA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 根據品質等級縮小圖片尺寸
        if quality <= 15:
            # 高壓縮：縮小到 35%
            new_size = (int(img.width * 0.35), int(img.height * 0.35))
            if new_size[0] > 50 and new_size[1] > 50:
                img = img.resize(new_size, Image.Resampling.LANCZOS)
        elif quality <= 50:
            # 中壓縮：縮小到 60%
            new_size = (int(img.width * 0.6), int(img.height * 0.6))
            if new_size[0] > 80 and new_size[1] > 80:
                img = img.resize(new_size, Image.Resampling.LANCZOS)

        # 儲存為 JPEG 並壓縮
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    except Exception:
        return image_data


def compress_pdf(input_bytes: bytes, quality: str, target_size_mb: float = 0) -> Tuple[bytes, dict]:
    """使用 Ghostscript 壓縮 PDF 檔案"""
    import subprocess
    import tempfile
    import os

    original_size = len(input_bytes)

    # Ghostscript 壓縮設定（更激進的參數）
    quality_settings = {
        "low": {
            "pdfsettings": "/prepress",
            "dpi": 300,
            "image_quality": 95
        },
        "medium": {
            "pdfsettings": "/ebook",
            "dpi": 150,
            "image_quality": 75
        },
        "high": {
            "pdfsettings": "/screen",
            "dpi": 72,
            "image_quality": 40
        },
        "extreme": {
            "pdfsettings": "/screen",
            "dpi": 50,
            "image_quality": 20
        }
    }
    settings = quality_settings.get(quality, quality_settings["medium"])

    def run_gs_compress(dpi: int, img_quality: int) -> bytes:
        """執行 Ghostscript 壓縮"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as input_file:
            input_file.write(input_bytes)
            input_path = input_file.name

        output_path = input_path.replace('.pdf', '_compressed.pdf')

        gs_command = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={settings["pdfsettings"]}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            '-dDetectDuplicateImages=true',
            '-dCompressFonts=true',
            '-dSubsetFonts=true',
            f'-dColorImageResolution={dpi}',
            f'-dGrayImageResolution={dpi}',
            f'-dMonoImageResolution={dpi}',
            '-dColorImageDownsampleType=/Bicubic',
            '-dGrayImageDownsampleType=/Bicubic',
            '-dMonoImageDownsampleType=/Bicubic',
            '-dDownsampleColorImages=true',
            '-dDownsampleGrayImages=true',
            '-dDownsampleMonoImages=true',
            f'-dJPEGQ={img_quality}',
            f'-sOutputFile={output_path}',
            input_path
        ]

        try:
            result = subprocess.run(gs_command, capture_output=True, timeout=180)
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, 'rb') as f:
                    compressed = f.read()
            else:
                compressed = input_bytes
        except Exception:
            compressed = input_bytes
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

        return compressed

    try:
        # 如果設定了目標大小，嘗試不同的 DPI 找到最佳壓縮
        if target_size_mb > 0:
            target_bytes = int(target_size_mb * 1024 * 1024)
            best_result = input_bytes

            # 嘗試不同的 DPI 值
            for dpi in [150, 100, 72, 50, 36, 24]:
                for img_q in [60, 40, 20, 10]:
                    compressed = run_gs_compress(dpi, img_q)
                    if len(compressed) <= target_bytes:
                        best_result = compressed
                        break
                    elif len(compressed) < len(best_result):
                        best_result = compressed
                if len(best_result) <= target_bytes:
                    break

            compressed_bytes = best_result
        else:
            # 使用預設設定壓縮
            compressed_bytes = run_gs_compress(settings["dpi"], settings["image_quality"])

        compressed_size = len(compressed_bytes)

        # 如果壓縮後變大，返回原始檔案
        if compressed_size >= original_size:
            compressed_bytes = input_bytes
            compressed_size = original_size

    except Exception:
        compressed_bytes = input_bytes
        compressed_size = original_size

    reduction = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0

    stats = {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "reduction": reduction
    }

    return compressed_bytes, stats


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

    # 讀取啟動畫面圖片
    splash_image_path = Path("assets/splash.png")
    if splash_image_path.exists():
        img_base64 = get_image_base64(str(splash_image_path))
    else:
        img_base64 = ""

    # 自訂 CSS 樣式 + 啟動畫面
    st.markdown(f"""
    <style>
        /* 啟動畫面樣式 */
        .splash-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: url('data:image/png;base64,{img_base64}');
            background-size: cover;
            background-position: center;
            background-color: #f5f5f5;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: center;
            z-index: 99999;
            animation: fadeOut 0.5s ease-out 4s forwards;
        }}
        .splash-progress {{
            width: 60%;
            max-width: 400px;
            margin-bottom: 80px;
        }}
        .splash-progress-bg {{
            background: rgba(255,255,255,0.5);
            border-radius: 10px;
            height: 10px;
            overflow: hidden;
        }}
        .splash-progress-bar {{
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            height: 100%;
            border-radius: 10px;
            animation: loading 3.5s ease-out forwards;
        }}
        .splash-text {{
            color: #555;
            font-size: 0.9rem;
            margin-top: 10px;
            font-family: "Microsoft JhengHei", sans-serif;
        }}
        @keyframes loading {{
            0% {{ width: 0%; }}
            100% {{ width: 100%; }}
        }}
        @keyframes fadeOut {{
            0% {{ opacity: 1; pointer-events: all; }}
            100% {{ opacity: 0; pointer-events: none; visibility: hidden; }}
        }}

        /* 主頁面樣式 */
        .title-container {{
            text-align: center;
            position: relative;
        }}
        .brand-text {{
            position: absolute;
            top: 0;
            left: 0;
            font-size: 0.85rem;
            color: #8B7355;
            font-family: "Microsoft JhengHei", "PingFang TC", serif;
        }}
        .main-title {{
            text-align: center;
            color: #5D4E37;
            margin-bottom: 0.5rem;
            font-family: "Microsoft JhengHei", "PingFang TC", serif;
        }}
        .sub-title {{
            text-align: center;
            color: #8B7355;
            font-size: 1.1rem;
            margin-bottom: 2rem;
            font-family: "Microsoft JhengHei", "PingFang TC", serif;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 10px 20px;
            font-size: 1rem;
        }}
    </style>

    <!-- 啟動畫面 -->
    <div class="splash-overlay" id="splash-screen">
        <div class="splash-progress">
            <div class="splash-progress-bg">
                <div class="splash-progress-bar"></div>
            </div>
            <p class="splash-text">載入中...</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 主標題區塊（含左上角品牌文字）
    st.markdown('''
    <div class="title-container">
        <span class="brand-text">亮言~</span>
        <h1 class="main-title">雲卷雲舒 · PDF 全能匠心</h1>
    </div>
    ''', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">化繁為簡凝雲墨，拆骨離魂鑄新篇</p>', unsafe_allow_html=True)

    # 建立分頁
    tab1, tab2, tab3 = st.tabs(["📦 壓縮", "✂️ 拆分", "🔗 合併"])

    # ===== 壓縮功能 =====
    with tab1:
        st.markdown("### 壓縮 PDF 檔案")
        st.markdown("上傳 PDF 檔案，減少檔案大小以便分享或儲存。使用 Ghostscript 專業壓縮引擎。")

        uploaded_file = st.file_uploader(
            "選擇要壓縮的 PDF 檔案",
            type=["pdf"],
            key="compress_uploader"
        )

        quality = st.radio(
            "選擇壓縮程度：",
            options=["low", "medium", "high", "extreme"],
            format_func=lambda x: {
                "low": "🟢 低度壓縮（300 DPI，高品質列印）",
                "medium": "🟡 中度壓縮（150 DPI，螢幕閱讀）",
                "high": "🔴 高度壓縮（72 DPI，最小檔案）",
                "extreme": "⚫ 極限壓縮（50 DPI，極低品質）"
            }[x],
            index=2,
            key="compress_quality"
        )

        # 目標大小選項
        use_target_size = st.checkbox("設定目標檔案大小", key="use_target_size")
        target_size_mb = 0.0
        if use_target_size:
            target_size_mb = st.slider(
                "目標大小 (MB)",
                min_value=0.5,
                max_value=10.0,
                value=4.0,
                step=0.5,
                key="target_size"
            )
            st.info(f"💡 將自動嘗試不同參數，找到最接近 {target_size_mb} MB 的壓縮結果（處理時間較長）")

        if quality == "extreme":
            st.warning("⚠️ 極限壓縮會大幅降低圖片品質，文字可能模糊。僅建議用於需要極小檔案的情況。")

        if uploaded_file is not None:
            st.markdown(f"**已上傳：** {uploaded_file.name} ({format_size(uploaded_file.size)})")

            if st.button("開始壓縮", key="compress_btn", type="primary"):
                with st.spinner("正在壓縮中，請稍候...（大型檔案可能需要 1-2 分鐘）"):
                    try:
                        compressed_bytes, stats = compress_pdf(uploaded_file.getvalue(), quality, target_size_mb)

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
            <p>亮言~ 雲卷雲舒 · PDF 全能匠心 - 免費開源工具</p>
            <p>所有檔案處理皆在伺服器端完成，處理完成後即刻刪除，不會保存您的檔案。</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# 主程式入口 - 直接顯示主應用程式
main_app()
