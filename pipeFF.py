import streamlit as st
from streamlit import caption, button, download_button, rerun, video, sidebar, set_page_config, expander, error, spinner, subheader, success, file_uploader, progress, write, warning, slider, stop, columns, session_state, info, header, text_input, code, selectbox, markdown, title
import subprocess
import os
import io
from pathlib import Path
import json

# 頁面設置
st.set_page_config(
    page_title="FFmpeg 視頻合併與轉場工具",
    page_icon="🎬",
    layout="wide"
)

# 應用標題
st.title("🎬 FFmpeg 視頻合併與轉場工具")
st.markdown("使用 FFmpeg pipe 直接處理視頻文件，無需臨時文件")

# 檢查 FFmpeg 是否可用
def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

# 初始化 session state
if 'videos' not in st.session_state:
    st.session_state.videos = []
if 'processed_video' not in st.session_state:
    st.session_state.processed_video = None

# 獲取視頻信息
def get_video_info(video_data):
    """使用 FFmpeg 獲取視頻基本信息"""
    try:
        # 使用 FFprobe 獲取視頻信息
        cmd = [
            'ffprobe', 
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            '-'
        ]
        
        result = subprocess.run(
            cmd, 
            input=video_data,
            capture_output=True, 
            check=True
        )
        
        info = json.loads(result.stdout)
        
        # 查找視頻流
        video_stream = next((stream for stream in info['streams'] if stream['codec_type'] == 'video'), None)
        
        if video_stream:
            duration = float(info['format']['duration'])
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            codec = video_stream['codec_name']
            
            return {
                'duration': duration,
                'resolution': f"{width}x{height}",
                'codec': codec
            }
    
    except Exception as e:
        st.warning(f"無法獲取視頻信息: {str(e)}")
    
    return None

# 側邊欄 - 上傳視頻
with st.sidebar:
    st.header("📁 視頻管理")
    
    uploaded_files = st.file_uploader(
        "上傳視頻文件",
        type=['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file not in [v['file'] for v in st.session_state.videos]:
                # 讀取文件內容
                video_data = uploaded_file.getvalue()
                video_info = get_video_info(video_data)
                
                st.session_state.videos.append({
                    'file': uploaded_file,
                    'name': uploaded_file.name,
                    'data': video_data,
                    'info': video_info
                })
        
        st.success(f"已上傳 {len(uploaded_files)} 個視頻文件")

    # 視頻列表管理
    if st.session_state.videos:
        st.subheader("視頻列表")
        for i, video in enumerate(st.session_state.videos):
            col1, col2 = st.columns([3, 1])
            with col1:
                info_text = video['name']
                if video['info']:
                    info_text += f" ({video['info']['resolution']}, {video['info']['duration']:.1f}s)"
                st.write(f"{i+1}. {info_text}")
            with col2:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.videos.pop(i)
                    st.rerun()

# 主內容區域
if not check_ffmpeg():
    st.error("❌ 未找到 FFmpeg。請確保 FFmpeg 已安裝並添加到系統 PATH 中。")
    st.stop()

if not st.session_state.videos:
    st.info("👆 請在左側上傳至少兩個視頻文件開始使用")
    st.stop()

# 轉場設置
st.header("🎞️ 轉場設置")

col1, col2, col3 = st.columns(3)

with col1:
    # 轉場效果選擇
    transition_effects = {
        "淡入淡出": "fade",
        "滑入": "slideleft",
        "滑出": "slideright",
        "向上滑動": "slideup",
        "向下滑動": "slidedown",
        "圓形": "circleopen",
        "方形": "rectcrop",
        "時鐘": "clock",
        "縮放": "zoom",
        "旋轉": "rotate",
        "像素化": "pixelize"
    }
    
    selected_effect = st.selectbox(
        "選擇轉場效果",
        options=list(transition_effects.keys()),
        index=0
    )

with col2:
    # 轉場持續時間
    transition_duration = st.slider(
        "轉場持續時間 (秒)",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.1
    )

with col3:
    # 輸出設置
    output_filename = st.text_input("輸出文件名", "merged_video.mp4")
    output_quality = st.selectbox(
        "輸出質量",
        ["高", "中", "低"],
        index=2
    )

# 高級設置
with st.expander("⚙️ 高級設置"):
    col1, col2 = st.columns(2)
    
    with col1:
        video_codec = st.selectbox("視頻編碼器", ["libx264", "libx265", "libvpx-vp9"], index=0)
        audio_codec = st.selectbox("音頻編碼器", ["aac", "libmp3lame", "copy"], index=0)
    
    with col2:
        frame_rate = st.selectbox(
            "幀率",
            ["保持原樣", "24", "25", "30", "60"],
            index=0
        )
        
        resolution = st.selectbox(
            "分辨率",
            ["保持原樣", "1920x1080", "1280x720", "854x480"],
            index=0
        )

# 預覽和處理
st.header("🎯 處理選項")

if len(st.session_state.videos) < 2:
    st.warning("⚠️ 需要至少兩個視頻才能添加轉場效果")
else:
    # 顯示視頻序列預覽
    st.subheader("視頻序列預覽")
    
    preview_cols = st.columns(min(4, len(st.session_state.videos)))
    for i, video in enumerate(st.session_state.videos):
        col_idx = i % 4
        with preview_cols[col_idx]:
            st.video(video['data'])
            info_text = video['name']
            if video['info']:
                info_text += f"\n{video['info']['resolution']} - {video['info']['duration']:.1f}s"
            st.caption(info_text)
            
            if i < len(st.session_state.videos) - 1:
                st.markdown(f"**↓ {selected_effect}**")

# 處理函數
def process_videos_with_pipes():
    """使用 FFmpeg pipe 處理視頻"""
    #try:
    # 構建 FFmpeg 命令
    cmd = ['ffmpeg', '-y']
    
    # 添加輸入管道
    for i in range(len(st.session_state.videos)):
        cmd.extend([
            '-i', 'pipe:0',  # 從 stdin 讀取
        ])
    
    # 構建 filter_complex
    filter_parts = []
    input_labels = []
    
    # 為每個輸入創建標籤
    for i in range(len(st.session_state.videos)):
        input_labels.append(f"[{i}:v]")
    
    # 構建轉場鏈
    for i in range(len(st.session_state.videos) - 1):
        if i == 0:
            # 第一個轉場
            filter_parts.append(f"{input_labels[i]}{input_labels[i+1]}xfade=transition={transition_effects[selected_effect]}:duration={transition_duration}")
        else:
            # 後續轉場
            filter_parts.append(f"[vf{i-1}]{input_labels[i+1]}xfade=transition={transition_effects[selected_effect]}:duration={transition_duration}")
        
        if i < len(st.session_state.videos) - 2:
            filter_parts.append(f"[vf{i}]")
    
    filter_complex = ";".join(filter_parts)
    
    # 添加 filter_complex 到命令
    cmd.extend(['-filter_complex', filter_complex])
    
    # 映射輸出視頻流
    cmd.extend(['-map', '[vf{}]'.format(len(st.session_state.videos)-2)])
    
    # 音頻處理 - 簡單連接
    cmd.extend(['-filter_complex', ';'.join([f'[{i}:a]' for i in range(len(st.session_state.videos))]) + f'concat=n={len(st.session_state.videos)}:v=0:a=1[outa]'])
    cmd.extend(['-map', '[outa]'])
    
    # 編碼設置
    quality_map = {"高": "18", "中": "23", "低": "28"}
    cmd.extend([
        '-c:v', video_codec,
        '-crf', quality_map[output_quality],
        '-c:a', audio_codec,
        '-movflags', '+faststart',
        '-f', 'mp4'
    ])
    
    # 分辨率設置
    if resolution != "保持原樣":
        cmd.extend(['-s', resolution])
    
    # 幀率設置
    if frame_rate != "保持原樣":
        cmd.extend(['-r', frame_rate])
    
    # 輸出到管道
    cmd.extend(['pipe:1'])
    
    # 顯示命令
    with st.expander("查看 FFmpeg 命令"):
        st.code(" ".join(cmd))
    
    # 啟動 FFmpeg 進程
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 發送所有輸入視頻數據
    for 視頻 in st.session_state.videos:
        code(len([視頻['data']]))
        #code(video['data'])
        process.stdin.write(視頻['data'])
    
    # 關閉輸入管道
    process.stdin.close()
    
    # 讀取輸出
    output_data = process.stdout.read()
    
    # 等待進程完成
    stderr_data = process.stderr.read().decode('utf-8')
    return_code = process.wait()
    
    if return_code == 0:
        return output_data, None
    else:
        return None, f"FFmpeg 錯誤: {stderr_data}"
        
    #except Exception as e:
    #    return None, f"處理錯誤: {str(e)}"

# 處理按鈕
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("🚀 開始合併視頻", use_container_width=True):
        if len(st.session_state.videos) < 2:
            st.error("需要至少兩個視頻文件")
        else:
            with st.spinner("正在處理視頻..."):
                progress_bar = st.progress(0)
                
                # 處理視頻
                output_data, error = process_videos_with_pipes()
                
                progress_bar.progress(100)
                
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.session_state.processed_video = output_data
                    st.success("✅ 視頻合併完成！")

# 顯示結果
if st.session_state.processed_video:
    st.header("📺 合併結果")
    
    # 顯示視頻
    st.video(st.session_state.processed_video)
    
    # 下載按鈕
    st.download_button(
        label="💾 下載合併後的視頻",
        data=st.session_state.processed_video,
        file_name=output_filename,
        mime="video/mp4",
        use_container_width=True
    )

# 替代方案：使用 concat demuxer（更簡單的方法）
with st.expander("🔄 替代方案：使用 concat demuxer"):
    st.markdown("""
    **對於簡單的視頻合併（無轉場），可以使用 concat demuxer：**
    
    ```bash
    ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
    ```
    
    這種方法更快，但不支持轉場效果。
    """)
    
    if st.button("使用 concat demuxer 快速合併（無轉場）"):
        # 創建文件列表
        file_list = "\n".join([f"file '{v['name']}'" for v in st.session_state.videos])
        
        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', '-',  # 從 stdin 讀取文件列表
            '-c', 'copy',
            '-f', 'mp4',
            'pipe:1'
        ]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 發送文件列表
        stdout, stderr = process.communicate(input=file_list.encode())
        
        if process.returncode == 0:
            st.session_state.processed_video = stdout
            st.success("✅ 快速合併完成！")
            st.rerun()
        else:
            st.error(f"合併失敗: {stderr.decode()}")

# 使用說明
with st.expander("📖 使用說明"):
    st.markdown("""
    ### 使用步驟：
    1. **上傳視頻**：在左側上傳至少兩個視頻文件
    2. **選擇轉場**：選擇喜歡的轉場效果和持續時間
    3. **調整設置**：根據需要調整輸出質量和編碼設置
    4. **開始處理**：點擊「開始合併視頻」按鈕
    5. **下載結果**：處理完成後下載合併後的視頻
    
    ### 技術特點：
    - 🚀 **無臨時文件**：使用 FFmpeg pipe 直接處理內存數據
    - ⚡ **高效處理**：避免磁盤 I/O 瓶頸
    - 🎨 **多種轉場**：支持 10+ 種專業轉場效果
    - 🔧 **靈活設置**：可調整編碼器、分辨率、質量等
    
    ### 注意事項：
    - 確保所有視頻的格式兼容
    - 大文件處理可能需要較多內存
    - 建議先使用小文件測試效果
    """)

# 頁腳
st.markdown("---")
st.markdown("🎬 使用 FFmpeg Pipe 和 Streamlit 構建的視頻處理工具")
