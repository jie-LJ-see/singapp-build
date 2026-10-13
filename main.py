# -*- coding: utf-8 -*-
"""
视唱练习 App（录音 + 回放版，可打包 Android / iOS）
数字与唱名：1=do 2=re 3=mi 4=fa 5=so 6=la 7=si

桌面运行：
    pip install kivy sounddevice soundfile
    python main.py
"""
import os
import random

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.text import LabelBase
from kivy.utils import platform

# ===== 平台判断：win / android / ios / macosx / linux =====
IS_ANDROID = platform == "android"
IS_IOS = platform == "ios"
IS_DESKTOP = not IS_ANDROID and not IS_IOS

# ===== 注册中文字体（Windows 黑体；方框就换成 msyh.ttc）=====
if IS_DESKTOP:
    LabelBase.register(name="cnfont", fn_regular="C:/Windows/Fonts/simhei.ttf")
FONT_CN = "cnfont" if IS_DESKTOP else "Roboto"

# ===== 唱名映射 =====
NOTES = {1: "do", 2: "re", 3: "mi", 4: "fa", 5: "so", 6: "la", 7: "si"}

# ===== 录音文件路径：手机上要写到可读写目录 =====
if IS_ANDROID:
    from android.storage import app_storage_path  # type: ignore
    REC_PATH = os.path.join(app_storage_path(), "record.wav")
elif IS_IOS:
    REC_PATH = os.path.join(os.path.expanduser("~/Documents"), "record.wav")
else:
    REC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "record.wav")


# ===== 录音 / 播放抽象层（按平台自动切换）=====
class AudioHelper:
    """统一接口：start / stop / play"""

    def __init__(self):
        self.recording = False
        self._sd = None
        self._sf = None
        if IS_DESKTOP:
            try:
                import sounddevice as sd
                import soundfile as sf
                self._sd = sd
                self._sf = sf
            except ImportError:
                pass

    def start(self):
        if self.recording:
            return
        if IS_ANDROID or IS_IOS:
            from plyer import recorder  # type: ignore
            recorder.start(filename=REC_PATH)
        else:
            if self._sd is None:
                raise RuntimeError("未安装 sounddevice/soundfile")
            # 桌面：最多录 15 秒
            self._sd.rec(int(15 * 44100), samplerate=44100, channels=1)
        self.recording = True

    def stop(self):
        if not self.recording:
            return
        if IS_ANDROID or IS_IOS:
            from plyer import recorder  # type: ignore
            recorder.stop()
        else:
            self._sd.stop()
            data, fs = self._sd.rec(
                int(15 * 44100), samplerate=44100, channels=1,
            ) if False else (None, None)
            # 取正在录的 buffer 并保存
            import numpy as np
            recorded = getattr(self, "_buf", None)
            self._sd.stop()
            # sounddevice.rec 返回的数组需要从主线程拿到
        self.recording = False

    def play(self):
        if IS_ANDROID or IS_IOS:
            from plyer import audio  # type: ignore
            if not os.path.exists(REC_PATH):
                raise RuntimeError("没有录音")
            audio.load(REC_PATH)
            audio.play()
        else:
            if self._sf is None or not os.path.exists(REC_PATH):
                raise RuntimeError("没有录音")
            data, fs = self._sf.read(REC_PATH)
            self._sd.play(data, fs)


# 桌面端要真的把录到的数据存下来，包装一下
if IS_DESKTOP:
    class DesktopRecorder:
        def __init__(self):
            self._sd = None
            self._sf = None
            self._rec = None
            self.recording = False
            try:
                import sounddevice as sd
                import soundfile as sf
                self._sd = sd
                self._sf = sf
            except ImportError:
                pass

        def start(self):
            if self.recording:
                return
            self._rec = self._sd.rec(
                int(15 * 44100), samplerate=44100, channels=1
            )
            self.recording = True

        def stop(self):
            if not self.recording:
                return
            self._sd.stop()
            self._sf.write(REC_PATH, self._rec, 44100)
            self.recording = False

        def play(self):
            if not os.path.exists(REC_PATH):
                raise RuntimeError("没有录音")
            data, fs = self._sf.read(REC_PATH)
            self._sd.play(data, fs)

    audio_helper = DesktopRecorder()
else:
    audio_helper = AudioHelper()


# ============ 主菜单 ============
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=40, padding=60)
        title = Label(text="唱名练习APP", font_name=FONT_CN, font_size=40)
        layout.add_widget(title)

        btn1 = Button(text="第一阶段", font_name=FONT_CN, font_size=28, size_hint_y=0.22)
        btn2 = Button(text="第二阶段", font_name=FONT_CN, font_size=28, size_hint_y=0.22)
        btn1.bind(on_press=self.go_stage1)
        btn2.bind(on_press=self.go_stage2)
        layout.add_widget(btn1)
        layout.add_widget(btn2)
        self.add_widget(layout)

    def go_stage1(self, *_):
        self.manager.current = "stage1"

    def go_stage2(self, *_):
        self.manager.current = "stage2"


# ============ 阶段页面 ============
class StageScreen(Screen):
    def __init__(self, title_text, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title_text
        self.nums = []
        self.name_labels = []
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", padding=20, spacing=12)
        root.add_widget(Label(text=self.title_text, font_name=FONT_CN,
                              font_size=22, size_hint_y=0.12))

        self.num_row = BoxLayout(spacing=15, size_hint_y=0.28)
        root.add_widget(self.num_row)

        # 状态提示
        self.status_label = Label(text="", font_name=FONT_CN, font_size=16,
                                  color=(0.2, 0.2, 0.5, 1), size_hint_y=0.15)
        root.add_widget(self.status_label)

        # 按钮行1：换一批 / 验证 / 返回
        row1 = BoxLayout(spacing=10, size_hint_y=0.15)
        b_new = Button(text="换一批", font_name=FONT_CN, font_size=18,
                       background_color=(0.35, 0.65, 0.95, 1))
        b_verify = Button(text="验证", font_name=FONT_CN, font_size=18,
                           background_color=(1, 0.55, 0.1, 1))
        b_back = Button(text="返回", font_name=FONT_CN, font_size=18,
                        background_color=(0.5, 0.5, 0.55, 1))
        b_new.bind(on_press=self.refresh)
        b_verify.bind(on_press=self.verify)
        b_back.bind(on_press=self.go_main)
        row1.add_widget(b_new)
        row1.add_widget(b_verify)
        row1.add_widget(b_back)
        root.add_widget(row1)

        # 按钮行2：录音 / 播放
        row2 = BoxLayout(spacing=10, size_hint_y=0.15)
        self.btn_rec = Button(text="开始录音", font_name=FONT_CN, font_size=18,
                              background_color=(0.9, 0.3, 0.3, 1))
        b_play = Button(text="播放录音", font_name=FONT_CN, font_size=18,
                         background_color=(0.4, 0.75, 0.4, 1))
        self.btn_rec.bind(on_press=self.toggle_rec)
        b_play.bind(on_press=self.play_rec)
        row2.add_widget(self.btn_rec)
        row2.add_widget(b_play)
        root.add_widget(row2)

        self.add_widget(root)
        self.refresh()

    def go_main(self, *_):
        self.manager.current = "main"

    def refresh(self, *_):
        self.num_row.clear_widgets()
        self.name_labels = []
        self.nums = self.make_numbers()
        self.status_label.text = "先看数字，再点「开始录音」唱一遍。"
        self.btn_rec.text = "开始录音"
        for n in self.nums:
            col = BoxLayout(orientation="vertical")
            col.add_widget(Label(text=str(n), font_size=40))
            lbl = Label(text="?", font_size=22, color=(0.2, 0.4, 0.85, 1))
            col.add_widget(lbl)
            self.num_row.add_widget(col)
            self.name_labels.append(lbl)

    def verify(self, *_):
        for lbl, n in zip(self.name_labels, self.nums):
            lbl.text = NOTES[n]

    def toggle_rec(self, *_):
        try:
            if not audio_helper.recording:
                audio_helper.start()
                self.btn_rec.text = "停止录音"
                self.status_label.text = "录音中… 唱完再点一次按钮。"
            else:
                audio_helper.stop()
                self.btn_rec.text = "开始录音"
                self.status_label.text = "录音已保存，点「播放录音」回听。"
        except Exception as e:
            self.status_label.text = "录音失败：%s" % e

    def play_rec(self, *_):
        try:
            audio_helper.play()
            self.status_label.text = "正在播放你的录音…"
        except Exception as e:
            self.status_label.text = "播放失败：%s" % e


class Stage1Screen(StageScreen):
    def __init__(self, **kwargs):
        super().__init__(title_text="第一阶段｜随机4个音符", **kwargs)

    def make_numbers(self):
        return [random.randint(1, 7) for _ in range(4)]


class Stage2Screen(StageScreen):
    def __init__(self, **kwargs):
        super().__init__(title_text="第二阶段｜1~7打乱全音符", **kwargs)

    def make_numbers(self):
        seq = list(range(1, 8))
        random.shuffle(seq)
        return seq


class SolfedgeApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(Stage1Screen(name="stage1"))
        sm.add_widget(Stage2Screen(name="stage2"))
        return sm


if __name__ == "__main__":
    SolfedgeApp().run()