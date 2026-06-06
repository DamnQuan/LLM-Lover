# 💕 AI 语音宝宝

长按说话，AI 女友用甜甜的语音回复你。基于 DeepSeek + Edge-TTS 的桌面语音助手。

## ✨ 功能

- 🎤 **长按录音** — 按住按钮说话，松开自动发送
- 🧠 **AI 对话** — DeepSeek API 驱动，扮演可爱女友角色
- 🔊 **语音合成** — Microsoft Edge TTS 自然女声朗读回复
- 🎀 **可爱界面** — 粉色系 customtkinter 桌面窗口
- 💬 **对话记忆** — 保留最近 20 条上下文，聊天更连贯
- 🔇 **播放锁定** — AI 说话时自动禁用录音，避免冲突
- 📝 **括号过滤** — 自动跳过括号内颜文字的朗读

## 📸 界面预览

```
┌──────────────────────────────────┐
│  💗  无敌超级最可爱的宝宝    💗  │
│ ──────────────────────────────── │
│                                  │
│  💕 宝宝：嗨~亲爱的！           │
│  你的无敌超级最可爱的宝宝来啦~   │
│                                  │
│  🧑 你：今天好想你呀           │
│                                  │
│  💕 宝宝：嘿嘿人家也想你啦~     │
│  今天有没有乖乖吃饭呀？         │
│                                  │
│ ──────────────────────────────── │
│  💤 准备就绪，按住按钮开始说话吧 │
│ ──────────────────────────────── │
│  ┌────────────────────────────┐  │
│  │     🎤  按住说话           │  │
│  └────────────────────────────┘  │
│  ⚙️ 设置 API Key   🗑️ 清空对话 │
└──────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- Windows / macOS / Linux
- 麦克风
- 网络连接

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 获取 DeepSeek API Key

前往 [platform.deepseek.com](https://platform.deepseek.com) 注册并获取 API Key。

### 4. 运行

```bash
python main.py
```

首次运行会弹出对话框，输入你的 DeepSeek API Key（自动保存到 `config.json`）。

## 🛠️ 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| GUI | `customtkinter` | 现代化 tkinter 封装，粉色主题 |
| 录音 | `sounddevice` + `numpy` | 低延迟实时录音 |
| 语音识别 | `SpeechRecognition` + Google API | 免费中文语音转文字 |
| AI 对话 | DeepSeek API (`deepseek-chat`) | OpenAI 兼容接口 |
| 语音合成 | `edge-tts` (Microsoft Xiaoxiao) | 最自然的中文女声 |
| 音频播放 | `pygame.mixer` | MP3 解码播放 |

## ⚙️ 配置说明

### TTS 语音调节

在 `main.py` 中修改以下参数：

```python
TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 语音角色

# 在 _edge_tts_generate 方法中：
rate="-5%"      # 语速：负值变慢，正值变快
pitch="+5Hz"    # 音高：正值更甜，负值更低
volume="+5%"    # 音量
```

> 其他可用语音：`zh-CN-XiaoyiNeural`（更甜少女音）、`zh-TW-HsiaoYuNeural`（台湾腔）

### AI 人设

编辑 `SYSTEM_PROMPT` 变量可自定义女友的说话风格和性格。

### 对话历史

默认保留最近 20 条消息作为上下文，可调整 `_call_deepseek_api` 中的 `len(self.messages) > 22` 阈值。

## 📁 项目结构

```
AI语音伴侣/
├── main.py            # 主程序（GUI + 录音 + API + TTS）
├── requirements.txt   # Python 依赖
├── config.json        # API Key 配置（自动生成）
└── README.md          # 本文件
```

## ❓ 常见问题

### 录音失败
- 检查麦克风是否已连接并在系统设置中授权
- Windows：设置 → 隐私 → 麦克风 → 允许桌面应用访问

### 语音识别不准
- 确保网络畅通（使用 Google 语音识别服务）
- 尽量在安静环境中说话，发音清晰

### TTS 报网络错误
- 检查网络连接，Edge-TTS 需要访问微软服务器
- 程序已内置 3 次重试机制，偶发网络波动会自动重试

### 声音不够甜/太假
- 调整 `pitch` 参数（建议 -5Hz ~ +15Hz）
- 换用 `zh-CN-XiaoyiNeural` 语音
- 调整 `rate` 参数改变语速

## 📄 许可

MIT License — 仅供个人学习和娱乐使用。
