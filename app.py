"""
豆包视频去水印+字幕工具 - 网页版
部署到 Hugging Face Spaces 后，朋友直接打开链接就能用
"""
import gradio as gr
import subprocess, os, tempfile, shutil, sys, io
from pathlib import Path

# ===== 水印位置 =====
WM1 = (1, 43, 298, 157)    # 左上
WM2 = (500, 1080, 219, 199)  # 右下

# ===== 字幕样式 =====
SUB_STYLE = ("FontName=Arial,FontSize=12,PrimaryColour=&HFFFFFF,"
             "OutlineColour=&H000000,BorderStyle=1,Outline=1,Shadow=1,MarginV=40")


def find_ffmpeg():
    """查找 ffmpeg（系统 PATH 或同目录）"""
    import shutil as sh
    ff = sh.which("ffmpeg")
    if ff:
        return ff
    local = Path(__file__).parent / "ffmpeg"
    if local.exists():
        return str(local)
    return None


def run_ffmpeg(cmd, desc=""):
    print(f"  {desc}...", end="", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = result.stderr.strip().split("\n")[-2:]
        print(f"\n  失败: {'; '.join(err)}")
        return False
    print(" 完成")
    return True


def fmt_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def process_video(video_path, add_subtitles, progress=gr.Progress()):
    """主处理函数"""
    path = Path(video_path)
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return None, "❌ 未找到 ffmpeg，服务器配置异常"

    temp_dir = Path(tempfile.mkdtemp())
    output_path = temp_dir / f"output_{path.name}"

    try:
        # 步骤 1: 去水印（如果有字幕再叠加）
        progress(0.1, desc="⏳ 处理视频中...")

        if add_subtitles:
            # 1a. 提取音频
            progress(0.2, desc="🔊 提取音频...")
            audio_path = temp_dir / "audio.wav"
            cmd1 = [ffmpeg_path, "-y", "-i", str(path), "-vn",
                    "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(audio_path)]
            if not run_ffmpeg(cmd1, "提取音频"):
                return None, "❌ 音频提取失败"

            # 1b. 语音识别
            progress(0.4, desc="🎙️ 正在识别语音（可能需要几分钟）...")
            try:
                import whisper
            except ImportError:
                return None, "❌ 缺少 whisper 库，无法生成字幕"

            model = whisper.load_model("tiny")
            result = model.transcribe(str(audio_path), language=None)

            srt_lines = []
            for i, seg in enumerate(result["segments"], 1):
                srt_lines.append(
                    f'{i}\n{fmt_time(seg["start"])} --> {fmt_time(seg["end"])}\n{seg["text"].strip()}\n'
                )
            srt_content = "\n".join(srt_lines)
            lang = result.get("language", "unknown")
            print(f"  识别语言: {lang}, {len(result['segments'])} 段字幕")

            srt_path = temp_dir / "subtitles.srt"
            srt_path.write_text(srt_content, encoding="utf-8")

            # 1c. 去水印 + 烧录字幕
            progress(0.7, desc="🎬 去水印+合成字幕...")
            srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")
            filter_str = (
                f"delogo=x={WM1[0]}:y={WM1[1]}:w={WM1[2]}:h={WM1[3]},"
                f"delogo=x={WM2[0]}:y={WM2[1]}:w={WM2[2]}:h={WM2[3]},"
                f"subtitles='{srt_escaped}':force_style='{SUB_STYLE}'"
            )
        else:
            # 仅去水印
            progress(0.5, desc="🎬 去水印中...")
            filter_str = (f"delogo=x={WM1[0]}:y={WM1[1]}:w={WM1[2]}:h={WM1[3]},"
                          f"delogo=x={WM2[0]}:y={WM2[1]}:w={WM2[2]}:h={WM2[3]}")

        cmd2 = [ffmpeg_path, "-y", "-i", str(path),
                "-vf", filter_str,
                "-c:v", "libx264", "-crf", "17", "-preset", "slow",
                "-c:a", "aac", "-b:a", "192k",
                str(output_path)]
        if not run_ffmpeg(cmd2, "处理视频"):
            return None, "❌ 视频处理失败"

        progress(0.95, desc="✅ 处理完成")
        in_size = os.path.getsize(path) / 1024 / 1024
        out_size = os.path.getsize(output_path) / 1024 / 1024
        summary = f"✅ 处理完成！{in_size:.0f}MB → {out_size:.0f}MB"
        if add_subtitles:
            summary += f" | 字幕语言: {lang}"

        return str(output_path), summary

    except Exception as e:
        return None, f"❌ 错误: {str(e)}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ===== Gradio 界面 =====
css = """
footer {display:none !important}
.gradio-container {max-width: 720px !important; margin: 0 auto !important}
h1 {text-align: center; margin-bottom: 0.5em}
.description {text-align: center; color: #666; margin-bottom: 1.5em}
"""

with gr.Blocks(title="豆包去水印工具", css=css) as demo:
    gr.Markdown(
        """
        # 🎬 豆包视频去水印 + 字幕工具
        <p class="description">上传视频，自动去除豆包水印，可选添加 AI 语音识别字幕</p>
        """
    )

    with gr.Row():
        with gr.Column():
            video_input = gr.Video(label="上传视频", sources="upload",
                                   height=300)
            with gr.Row():
                sub_checkbox = gr.Checkbox(label="🎙️ 添加 AI 字幕", value=True)
            with gr.Row():
                process_btn = gr.Button("🚀 开始处理", variant="primary", size="lg")
        with gr.Column():
            video_output = gr.Video(label="处理后视频", interactive=False, height=300)
            status = gr.Textbox(label="状态", show_label=False)

    process_btn.click(
        fn=process_video,
        inputs=[video_input, sub_checkbox],
        outputs=[video_output, status]
    )

    gr.Markdown(
        """
        ---
        **⚠️ 说明**
        - 视频越大处理越慢，建议上传不超过 200MB
        - AI 字幕需要额外处理时间（约视频时长的 1-2 倍）
        - 处理完成后右键视频可下载
        """
    )

if __name__ == "__main__":
    demo.launch()
