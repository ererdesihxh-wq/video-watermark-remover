# 豆包视频去水印 + AI 字幕工具

基于 Gradio 的 Web 应用，上传视频自动去除豆包水印，可选 AI 语音识别生成字幕。

## 功能

- 🎬 去除豆包视频水印（左上 + 右下）
- 🎙️ AI 语音识别生成字幕（基于 Whisper）
- 🌐 Web 界面，浏览器直接使用
- 📥 处理完成后可下载视频

## 本地部署

```bash
pip install -r requirements.txt
python app.py
```

需要安装 ffmpeg 并在系统 PATH 中可用。

## 技术栈

- Gradio — Web 界面
- FFmpeg — 视频处理（delogo 滤镜）
- OpenAI Whisper — 语音识别
