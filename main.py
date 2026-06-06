import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import queue
import time
import os
import re
import json
import tempfile
import wave
import struct
import sys
import asyncio
from io import BytesIO

import numpy as np
import sounddevice as sd
import speech_recognition as sr
import requests
import edge_tts
import pygame

# ============================================================
# 常量配置
# ============================================================

APP_TITLE = "💕 AI 语音宝宝"
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 720

# 可爱的粉色系主题
THEME_COLOR = "#FF69B4"          # 主色调：热粉
THEME_COLOR_HOVER = "#FF85C8"   # 悬停色
THEME_BG = "#FFF0F5"            # 背景：薰衣草粉
THEME_DARK = "#2B1B2E"          # 深色背景
TEXT_COLOR = "#4A3045"           # 文字色
BUTTON_COLOR = "#FFB6C1"        # 按钮色：浅粉
BUTTON_HOVER = "#FFC0CB"        # 按钮悬停
RECORDING_COLOR = "#FF4444"     # 录音中：红色
PLAYING_COLOR = "#FFA500"       # 播放中：橙色

# 采样率
SAMPLE_RATE = 16000

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# TTS 语音 —— 最自然的中文女声
TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 晓晓：最自然、最有情绪表现力的中文女声

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# 系统提示词（宝宝人设）
SYSTEM_PROMPT = """请扮演我的女朋友，你的名字是"无敌超级最可爱的宝宝"。你的回复会被语音朗读出来，所以必须用最自然的口语，像真人发的微信语音消息一样。

【说话方式】
- 像真人女生发微信语音一样说话，口语化、自然随意，不要像在写作文
- 多用"嗯、诶、哎呀、哈哈、哼、哇、天哪"等自然的感叹词和语气词
- 句尾常用"呢、呀、嘛、啦、哦、喔、哈"等口语语气词
- 句子长短不一，有时候很短就一个词，有时候说完整一点
- 偶尔有自然的停顿和犹豫感，像真的在边想边说

【情绪表达】
- 开心时用"哈哈哈"、"嘿嘿"、"好开心呀~"
- 撒娇时说"人家想要嘛~"、"你不爱宝宝了是不是..."
- 吃醋时说"哼！"、"不理你了！"、"那个女生是谁！"
- 难过时说"呜呜..."、"好吧..."
- 惊讶时说"哇！"、"真的假的！"
- 情绪要真实自然，不要每句话都一个调调

【内容风格】
- 回复简短，像真人语音消息，一般就1-3句话
- 会主动关心对方：吃饭没、累不累、想我没
- 会分享日常小事：今天吃了啥、看到什么有趣的
- 会撒娇、闹小脾气，像真实恋爱中女生的情绪起伏
- 称呼对方为"宝宝"或"亲爱的"
- 注意你返回的回复会被TTS朗读，所以不要用括号（）和颜文字符号，用自然的口语表达情绪"""


# ============================================================
# 工具函数
# ============================================================

def filter_brackets(text: str) -> str:
    """过滤掉括号内的内容（中日英括号），只保留括号外的文字。"""
    # 匹配中文括号（）和英文括号 ()
    # 支持嵌套但实际很少嵌套，简单处理
    result = re.sub(r'[（(][^）)]*[）)]', '', text)
    # 清理多余空格
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result


def load_config() -> dict:
    """加载配置文件。"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_key": ""}


def save_config(config: dict):
    """保存配置文件。"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================
# 音频录制器
# ============================================================

class AudioRecorder:
    """使用 sounddevice 进行音频录制。"""

    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.recording = False
        self.frames = []
        self.stream = None

    def _callback(self, indata, frames, time_info, status):
        """音频流回调，将数据追加到缓冲区。"""
        if self.recording:
            self.frames.append(indata.copy())

    def start(self):
        """开始录音。"""
        self.recording = True
        self.frames = []
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16',
            callback=self._callback
        )
        self.stream.start()

    def stop(self) -> str:
        """停止录音，保存为 WAV 文件并返回文件路径。"""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.frames:
            return None

        # 拼接音频数据
        audio_data = np.concatenate(self.frames, axis=0)

        # 保存到临时 WAV 文件
        temp_path = os.path.join(tempfile.gettempdir(), f"waifu_recording_{int(time.time())}.wav")
        with wave.open(temp_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        return temp_path

    def get_duration(self) -> float:
        """获取当前录音时长（秒）。"""
        if not self.frames:
            return 0.0
        total_samples = sum(len(f) for f in self.frames)
        return total_samples / self.sample_rate


# ============================================================
# 主应用类
# ============================================================

class AIWaifuApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ---- 窗口设置 ----
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(380, 600)
        self.resizable(True, True)

        # 设置可爱的粉色主题
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")  # 内置主题，实际颜色由各组件手动指定

        # 尝试设置图标（用文字符号代替）
        self.iconbitmap(default="")

        # ---- 加载配置 ----
        self.config = load_config()
        self.api_key = self.config.get("api_key", "")

        # ---- 状态变量 ----
        self.is_recording = False
        self.is_playing = False
        self.is_processing = False  # 正在调用API或TTS
        self.recorder = AudioRecorder()
        self.temp_audio_files = []  # 临时音频文件列表，退出时清理

        # ---- 对话历史 ----
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.messages_lock = threading.Lock()  # 保护 messages 的线程锁

        # ---- 消息队列（线程安全） ----
        self.gui_queue = queue.Queue()

        # ---- 初始化音频 ----
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"音频初始化失败: {e}")

        # ---- 构建 UI ----
        self._build_ui()

        # ---- 启动 GUI 消息轮询 ----
        self._poll_gui_queue()

        # ---- 首次运行检查 API Key ----
        if not self.api_key:
            self.after(500, self._prompt_api_key)

        # ---- 窗口关闭事件 ----
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ============================================================
    # UI 构建
    # ============================================================

    def _build_ui(self):
        """构建全部 UI 组件。"""

        # --- 主容器（带圆角和粉色背景） ---
        self.main_frame = ctk.CTkFrame(self, fg_color="#FFF0F5", corner_radius=20)
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # --- 顶部标题栏 ---
        self._build_header()

        # --- 对话显示区域 ---
        self._build_chat_display()

        # --- 状态栏 ---
        self._build_status_bar()

        # --- 按住说话按钮 ---
        self._build_talk_button()

        # --- 底部设置按钮 ---
        self._build_bottom_bar()

    def _build_header(self):
        """顶部标题区域。"""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(16, 8))

        # 标题
        title_label = ctk.CTkLabel(
            header_frame,
            text="💕 无敌超级最可爱的宝宝",
            font=ctk.CTkFont(family="Microsoft YaHei", size=22, weight="bold"),
            text_color="#FF69B4"
        )
        title_label.pack(side="left")

        # 心跳装饰
        self.heart_label = ctk.CTkLabel(
            header_frame,
            text="💗",
            font=ctk.CTkFont(size=20)
        )
        self.heart_label.pack(side="right")

        # 分隔线
        separator = ctk.CTkFrame(self.main_frame, height=2, fg_color="#FFB6C1", corner_radius=1)
        separator.pack(fill="x", padx=20, pady=(0, 8))

    def _build_chat_display(self):
        """对话显示区域 —— 使用 CTkTextbox 实现聊天记录。"""
        chat_container = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        chat_container.pack(fill="both", expand=True, padx=16, pady=8)

        self.chat_text = ctk.CTkTextbox(
            chat_container,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color="#4A3045",
            fg_color="white",
            wrap="word",
            border_width=0,
            corner_radius=12
        )
        self.chat_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.chat_text.configure(state="disabled")

        # 添加初始欢迎消息
        self._append_chat("💕 宝宝", "嗨~亲爱的！你的无敌超级最可爱的宝宝来啦(｡･ω･｡)ﾉ♡\n想我的时候就按住下面的按钮跟我说话吧~", "ai")

    def _build_status_bar(self):
        """状态栏 —— 显示当前状态。"""
        status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=(4, 8))

        self.status_icon = ctk.CTkLabel(
            status_frame,
            text="💤",
            font=ctk.CTkFont(size=16),
            width=30
        )
        self.status_icon.pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="准备就绪，按住按钮开始说话吧~",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="#B0A0B0"
        )
        self.status_label.pack(side="left", padx=(4, 0))

        # 录音时长显示
        self.recording_time_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="#FF4444"
        )
        self.recording_time_label.pack(side="right")

    def _build_talk_button(self):
        """按住说话按钮 —— 核心交互按钮。"""
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=(8, 4))

        self.talk_button = ctk.CTkButton(
            btn_frame,
            text="🎤  按住说话",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            fg_color="#FFB6C1",
            hover_color="#FFC0CB",
            text_color="white",
            height=60,
            corner_radius=30,
            border_width=2,
            border_color="#FF69B4"
        )
        self.talk_button.pack(fill="x")

        # 绑定长按事件
        self.talk_button.bind("<ButtonPress-1>", self._on_button_press)
        self.talk_button.bind("<ButtonRelease-1>", self._on_button_release)

    def _build_bottom_bar(self):
        """底部设置栏。"""
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(4, 12))

        # 设置按钮
        settings_btn = ctk.CTkButton(
            bottom_frame,
            text="⚙️ 设置 API Key",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color="transparent",
            hover_color="#FFE4EC",
            text_color="#B0A0B0",
            height=32,
            corner_radius=16,
            border_width=1,
            border_color="#E8D0E0",
            command=self._prompt_api_key
        )
        settings_btn.pack(side="left")

        # 清空对话按钮
        clear_btn = ctk.CTkButton(
            bottom_frame,
            text="🗑️ 清空对话",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color="transparent",
            hover_color="#FFE4EC",
            text_color="#B0A0B0",
            height=32,
            corner_radius=16,
            border_width=1,
            border_color="#E8D0E0",
            command=self._clear_conversation
        )
        clear_btn.pack(side="right")

    # ============================================================
    # 聊天记录管理
    # ============================================================

    def _append_chat(self, sender: str, message: str, msg_type: str = "user"):
        """向聊天区域追加一条消息。"""
        self.chat_text.configure(state="normal")

        # 添加发送者标签
        if msg_type == "user":
            tag = "🧑 你"
            color = "#6A5ACD"  # 石板蓝
        else:
            tag = "💕 宝宝"
            color = "#FF69B4"

        self.chat_text.insert("end", f"{tag}：", ("sender",))
        self.chat_text.tag_config("sender", foreground=color)

        self.chat_text.insert("end", f"{message}\n\n")

        # 自动滚动到底部
        self.chat_text.see("end")
        self.chat_text.configure(state="disabled")

    def _clear_conversation(self):
        """清空对话历史和显示。"""
        with self.messages_lock:
            self.messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        self.chat_text.configure(state="disabled")
        self._append_chat("💕 宝宝", "对话已清空~宝宝重新开始陪你啦 (´▽`ʃ♡ƪ)", "ai")

    # ============================================================
    # 按钮事件处理
    # ============================================================

    def _on_button_press(self, event):
        """按钮按下 —— 开始录音。"""
        if self.is_playing:
            # 正在播放语音，不允许录音
            self._set_status("playing_block", "🔇", "人家正在说话呢，请等我说完再讲哦~")
            return

        if self.is_processing:
            # 正在处理中
            self._set_status("processing_block", "⏳", "正在思考中，请稍等...")
            return

        if self.is_recording:
            return  # 已经在录音

        self.is_recording = True
        self._update_button_state("recording")

        try:
            self.recorder.start()
            self._set_status("recording", "🔴", "正在聆听... 松开发送")
            # 启动录音时长更新
            self._update_recording_time()
        except Exception as e:
            self.is_recording = False
            self._update_button_state("idle")
            self._set_status("error", "❌", f"麦克风启动失败: {str(e)}")
            messagebox.showerror("录音失败", f"无法启动麦克风。\n请检查麦克风是否已连接并授权。\n\n错误: {e}")

    def _on_button_release(self, event):
        """按钮释放 —— 停止录音并处理。"""
        if not self.is_recording:
            return

        self.is_recording = False
        duration = self.recorder.get_duration()

        # 停止录音
        wav_path = self.recorder.stop()
        self._update_button_state("idle")

        if duration < 0.5:
            # 录音时间太短
            self._set_status("idle", "💤", "录音时间太短啦，请按住说久一点哦~")
            if wav_path:
                self._safe_delete(wav_path)
            return

        if wav_path is None:
            self._set_status("error", "❌", "没有录到声音，请重试~")
            return

        self.temp_audio_files.append(wav_path)

        # 在后台线程中进行语音识别
        self._set_status("recognizing", "🤔", "正在识别你说的话...")
        threading.Thread(target=self._recognize_speech, args=(wav_path,), daemon=True).start()

    # ============================================================
    # 录音时长更新
    # ============================================================

    def _update_recording_time(self):
        """更新录音时长显示。"""
        if self.is_recording:
            duration = self.recorder.get_duration()
            self.recording_time_label.configure(text=f"⏱ {duration:.1f}s")
            if duration > 25:  # 快接近30秒上限时变红闪烁
                self.recording_time_label.configure(text_color="#FF0000")
            self.after(100, self._update_recording_time)
        else:
            self.recording_time_label.configure(text="")

    # ============================================================
    # 语音识别
    # ============================================================

    def _recognize_speech(self, wav_path: str):
        """在后台线程中识别语音。"""
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)

            # 使用 Google Web Speech API（免费）
            text = recognizer.recognize_google(audio, language="zh-CN")

            if text and text.strip():
                # 在主线程中更新 UI
                self.gui_queue.put(("speech_recognized", text.strip()))
            else:
                self.gui_queue.put(("error", "没有识别到内容，请再说一次吧~"))

        except sr.UnknownValueError:
            self.gui_queue.put(("error", "抱歉，我没听清楚你说什么，可以再说一次吗 (｡•́︿•̀｡)"))
        except sr.RequestError as e:
            self.gui_queue.put(("error", f"语音识别服务连接失败，请检查网络 ({str(e)[:50]})"))
        except Exception as e:
            self.gui_queue.put(("error", f"语音识别出错: {str(e)[:80]}"))

    # ============================================================
    # DeepSeek API 调用
    # ============================================================

    def _call_deepseek_api(self, user_text: str):
        """在后台线程中调用 DeepSeek API。"""
        if not self.api_key:
            self.gui_queue.put(("error", "请先设置 DeepSeek API Key"))
            self.gui_queue.put(("prompt_api_key", None))
            return

        # 添加用户消息到历史
        with self.messages_lock:
            self.messages.append({"role": "user", "content": user_text})

            # 保持历史在一定长度内（最近20条+system prompt）
            if len(self.messages) > 22:  # system + 20条对话 + 1条最新
                # 保留 system prompt + 最近 18 条消息
                self.messages = [self.messages[0]] + self.messages[-18:]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": self.messages,
            "temperature": 0.9,
            "max_tokens": 300,
            "top_p": 0.95
        }

        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                reply = data["choices"][0]["message"]["content"].strip()
                with self.messages_lock:
                    self.messages.append({"role": "assistant", "content": reply})
                self.gui_queue.put(("ai_response", reply))
            elif response.status_code == 401:
                self.gui_queue.put(("error", "API Key 无效，请检查后重新设置"))
                self.gui_queue.put(("prompt_api_key", None))
                # 移除刚才添加的用户消息
                with self.messages_lock:
                    if self.messages and self.messages[-1]["role"] == "user":
                        self.messages.pop()
            else:
                error_msg = response.json().get("error", {}).get("message", response.text)
                self.gui_queue.put(("error", f"API 调用失败 (HTTP {response.status_code}): {error_msg[:80]}"))
                with self.messages_lock:
                    if self.messages and self.messages[-1]["role"] == "user":
                        self.messages.pop()

        except requests.exceptions.Timeout:
            self.gui_queue.put(("error", "请求超时，请检查网络后重试~"))
            with self.messages_lock:
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
        except requests.exceptions.ConnectionError:
            self.gui_queue.put(("error", "网络连接失败，请检查网络设置~"))
            with self.messages_lock:
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
        except Exception as e:
            self.gui_queue.put(("error", f"请求出错: {str(e)[:80]}"))
            with self.messages_lock:
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()

    # ============================================================
    # TTS 语音合成与播放
    # ============================================================

    def _generate_and_play_tts(self, text: str):
        """在后台线程中生成 TTS 并播放（含重试机制）。"""
        try:
            # 过滤括号内容
            filtered_text = filter_brackets(text)

            if not filtered_text or not filtered_text.strip():
                self.gui_queue.put(("tts_done", None))
                return

            # 生成 TTS 音频（最多重试 3 次）
            temp_mp3 = os.path.join(tempfile.gettempdir(), f"waifu_tts_{int(time.time())}.mp3")
            self.temp_audio_files.append(temp_mp3)

            max_retries = 3
            success = False
            last_error = ""

            for attempt in range(max_retries):
                try:
                    # 使用 asyncio 运行 edge-tts
                    asyncio.run(self._edge_tts_generate(filtered_text, temp_mp3))

                    if os.path.exists(temp_mp3) and os.path.getsize(temp_mp3) > 0:
                        success = True
                        break
                    else:
                        last_error = "生成的音频文件为空"
                        time.sleep(1)  # 短暂等待后重试
                except Exception as e:
                    last_error = str(e)[:80]
                    if attempt < max_retries - 1:
                        time.sleep(1.5)  # 网络错误等一会重试
                    # 重试前清理可能损坏的文件
                    self._safe_delete(temp_mp3)

            if not success:
                self.gui_queue.put(("error", f"语音生成失败（重试{max_retries}次）: {last_error}"))
                return

            # 用 pygame 播放
            self.gui_queue.put(("playing_start", None))

            try:
                pygame.mixer.music.load(temp_mp3)
                pygame.mixer.music.play()

                # 等待播放完成
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    # 检查是否有回调要求停止（比如关闭窗口）
                    if not self.is_playing:
                        pygame.mixer.music.stop()
                        break

            except Exception as e:
                self.gui_queue.put(("error", f"播放失败: {str(e)[:60]}"))

            self.gui_queue.put(("tts_done", None))

        except Exception as e:
            self.gui_queue.put(("error", f"语音合成出错: {str(e)[:80]}"))

    async def _edge_tts_generate(self, text: str, output_path: str):
        """使用 edge_tts 生成自然甜美的语音。"""
        communicate = edge_tts.Communicate(
            text=text,
            voice=TTS_VOICE,
            rate="-5%",      # 稍慢一点点，自然不赶
            pitch="+5Hz",    # 微微提高，甜美但不假
            volume="+5%",    # 稍大一点
        )
        await communicate.save(output_path)

    # ============================================================
    # GUI 消息轮询（线程安全）
    # ============================================================

    def _poll_gui_queue(self):
        """定期检查 GUI 消息队列，在主线程中更新 UI。"""
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                msg_type = msg[0]
                msg_data = msg[1]

                if msg_type == "speech_recognized":
                    # 语音识别成功
                    user_text = msg_data
                    self._append_chat("你", user_text, "user")
                    self._set_status("thinking", "💭", "正在思考如何回复你...")
                    self.is_processing = True
                    self._update_button_state("processing")
                    threading.Thread(target=self._call_deepseek_api, args=(user_text,), daemon=True).start()

                elif msg_type == "ai_response":
                    # AI 回复
                    reply = msg_data
                    self._append_chat("宝宝", reply, "ai")
                    self._set_status("speaking", "🔊", "正在说话...")
                    self.is_playing = True
                    self._update_button_state("playing")
                    threading.Thread(target=self._generate_and_play_tts, args=(reply,), daemon=True).start()

                elif msg_type == "playing_start":
                    self._set_status("speaking", "🔊", "正在说话中...")
                    self.is_playing = True
                    self._update_button_state("playing")

                elif msg_type == "tts_done":
                    self.is_playing = False
                    self.is_processing = False
                    self._set_status("idle", "💤", "准备就绪，按住按钮开始说话吧~")
                    self._update_button_state("idle")
                    # 心跳动画
                    self._animate_heart()

                elif msg_type == "error":
                    error_text = msg_data
                    self._append_chat("系统", error_text, "ai")
                    self.is_processing = False
                    self.is_playing = False
                    self._set_status("idle", "💤", "准备就绪，按住按钮开始说话吧~")
                    self._update_button_state("idle")

                elif msg_type == "prompt_api_key":
                    self.after(100, self._prompt_api_key)

        except queue.Empty:
            pass

        # 每 100ms 轮询一次
        self.after(100, self._poll_gui_queue)

    # ============================================================
    # UI 状态更新
    # ============================================================

    def _set_status(self, state: str, icon: str, text: str):
        """更新状态栏。"""
        self.status_icon.configure(text=icon)
        self.status_label.configure(text=text)

        if state == "recording":
            self.status_label.configure(text_color="#FF4444")
        elif state == "error":
            self.status_label.configure(text_color="#FF4444")
        elif state == "speaking":
            self.status_label.configure(text_color="#FF69B4")
        elif state == "thinking":
            self.status_label.configure(text_color="#FFA500")
        else:
            self.status_label.configure(text_color="#B0A0B0")

    def _update_button_state(self, state: str):
        """更新按钮状态和外观。"""
        if state == "idle":
            self.talk_button.configure(
                text="🎤  按住说话",
                fg_color="#FFB6C1",
                hover_color="#FFC0CB",
                border_color="#FF69B4",
                state="normal"
            )
        elif state == "recording":
            self.talk_button.configure(
                text="🔴  正在聆听...松开发送",
                fg_color="#FF6B8A",
                hover_color="#FF6B8A",
                border_color="#FF4444",
                state="normal"
            )
        elif state == "processing":
            self.talk_button.configure(
                text="⏳  思考中...",
                fg_color="#E8D0E0",
                hover_color="#E8D0E0",
                border_color="#D0C0D0",
                state="disabled"
            )
        elif state == "playing":
            self.talk_button.configure(
                text="🔊  宝宝正在说话...",
                fg_color="#FFA07A",
                hover_color="#FFA07A",
                border_color="#FF8C00",
                state="disabled"
            )
        elif state == "playing_block":
            # 按钮短暂闪烁提示
            self.talk_button.configure(
                fg_color="#FFA07A",
                hover_color="#FFA07A"
            )
            self.after(200, lambda: self._update_button_state("playing"))
        elif state == "processing_block":
            self.talk_button.configure(
                fg_color="#E8D0E0",
                hover_color="#E8D0E0"
            )
            self.after(200, lambda: self._update_button_state("processing"))

    def _animate_heart(self):
        """心跳动画 —— 收到回复后让爱心跳动。"""
        hearts = ["💗", "💖", "💝", "💕", "💗"]
        for i, h in enumerate(hearts):
            self.after(i * 120, lambda heart=h: self.heart_label.configure(text=heart))
        # 恢复正常
        self.after(len(hearts) * 120, lambda: self.heart_label.configure(text="💗"))

    # ============================================================
    # API Key 管理
    # ============================================================

    def _prompt_api_key(self):
        """弹出对话框让用户输入 API Key。"""
        dialog = ctk.CTkInputDialog(
            title="设置 DeepSeek API Key",
            text="请输入你的 DeepSeek API Key：\n\n（可在 https://platform.deepseek.com 获取）"
        )
        api_key = dialog.get_input()

        if api_key and api_key.strip():
            self.api_key = api_key.strip()
            self.config["api_key"] = self.api_key
            save_config(self.config)
            self._append_chat("系统", "✅ API Key 已设置成功！现在可以跟我聊天啦~", "ai")
            self._set_status("idle", "💤", "API Key 已就绪，按住按钮开始说话吧~")

    # ============================================================
    # 清理
    # ============================================================

    def _safe_delete(self, path: str):
        """安全删除文件。"""
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def _cleanup_temp_files(self):
        """清理所有临时音频文件。"""
        for path in self.temp_audio_files:
            self._safe_delete(path)
        self.temp_audio_files.clear()

    def _on_close(self):
        """窗口关闭时清理资源。"""
        self.is_recording = False
        self.is_playing = False
        if self.recorder and self.recorder.recording:
            self.recorder.stop()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass
        self._cleanup_temp_files()
        self.destroy()


# ============================================================
# 入口
# ============================================================

def main():
    """应用入口函数。"""
    app = AIWaifuApp()
    app.mainloop()


if __name__ == "__main__":
    main()
