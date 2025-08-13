# gui_app.py
import customtkinter as ctk
import queue
import webbrowser
from controller import AppController, AppState
from ffmpeg_manager import FFmpegManager
from logger import UILogger
from config_manager import ConfigManager
from stream_finder import StreamFinder
from youtube_manager import YouTubeManager

class AppGUI(ctk.CTk):
    """应用程序的主GUI窗口，经过美学和功能性重构。"""
    
    def __init__(self):
        super().__init__()
        self.title("我从山上来 24/7 全自动转播系统 (v2.1 修复版)")
        self.geometry("900x700")
        ctk.set_appearance_mode("dark") # 设定现代化的深色主题

        self.log_queue = queue.Queue()
        
        # --- 实例化所有模块 ---
        self.logger = UILogger(self.log_queue)
        self.config_manager = ConfigManager(self.logger, 'yt.ini')
        self.youtube_manager = YouTubeManager(self.logger, self.config_manager)
        self.ffmpeg_manager = FFmpegManager(self.logger, self.config_manager)
        self.stream_finder = StreamFinder(self.logger, self.config_manager)
        
        # 实例化大脑，并把自己(self)传进去，用于回调
        self.controller = AppController(
            self, self.logger, self.config_manager, self.youtube_manager,
            self.ffmpeg_manager, self.stream_finder
        )

        self.create_widgets()
        self.log_updater()

        # 绑定窗口关闭事件到正确的处理函数
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """创建UI界面上的所有组件。"""
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 创建左侧主区域 (日志) ---
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        log_label = ctk.CTkLabel(left_frame, text="运行日志", font=ctk.CTkFont(size=16, weight="bold"))
        log_label.grid(row=0, column=0, padx=10, pady=(0, 5), sticky="w")

        self.log_textbox = ctk.CTkTextbox(left_frame, state="disabled", wrap="word", font=("Consolas", 12))
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 0), sticky="nsew")

        # --- 创建右侧信息与控制面板 ---
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        
        # --- 状态面板 ---
        status_panel = ctk.CTkFrame(right_frame)
        status_panel.grid(row=0, column=0, padx=10, pady=10, sticky="new")
        status_panel.grid_columnconfigure(0, weight=1)

        status_title = ctk.CTkLabel(status_panel, text="实时状态", font=ctk.CTkFont(size=16, weight="bold"))
        status_title.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.status_label = ctk.CTkLabel(status_panel, text="⚪ 空闲", font=ctk.CTkFont(size=20, weight="bold"), text_color="gray")
        self.status_label.grid(row=1, column=0, padx=15, pady=5, sticky="w")
        
        self.source_label = ctk.CTkLabel(status_panel, text="来源: --", font=ctk.CTkFont(size=12), wraplength=220, justify="left")
        self.source_label.grid(row=2, column=0, padx=15, pady=(5, 10), sticky="w")

        self.ffmpeg_label = ctk.CTkLabel(status_panel, text="FFmpeg PID: --", font=ctk.CTkFont(size=12))
        self.ffmpeg_label.grid(row=3, column=0, padx=15, pady=(0, 10), sticky="w")

        self.youtube_link_label = ctk.CTkLabel(status_panel, text="打开YouTube直播间", text_color="#5D9EFF", cursor="hand2")
        self.youtube_link_label.grid(row=4, column=0, padx=15, pady=(0, 15), sticky="w")
        self.youtube_link_label.bind("<Button-1>", self.open_youtube_link)
        self.youtube_link_label.grid_remove() # 默认隐藏

        # --- 控制面板 ---
        control_panel = ctk.CTkFrame(right_frame)
        control_panel.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        control_panel.grid_columnconfigure(0, weight=1)
        control_panel.grid_columnconfigure(1, weight=1)

        self.start_button = ctk.CTkButton(control_panel, text="✅ 开始运行", command=self.start_app, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_button.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")

        self.stop_button = ctk.CTkButton(control_panel, text="🛑 停止运行", command=self.stop_app, state="disabled", fg_color="#D32F2F", hover_color="#B71C1C", font=ctk.CTkFont(size=14, weight="bold"))
        self.stop_button.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="ew")

    def update_status_display(self, state: AppState, controller_ref):
        """由控制器调用，根据当前状态更新整个GUI的状态面板。"""
        state_map = {
            AppState.IDLE: ("⚪ 空闲", "gray"),
            AppState.INITIALIZING: ("🛠️ 初始化中...", "#5D9EFF"),
            AppState.SCANNING: ("📡 扫描直播源...", "#5D9EFF"),
            AppState.STREAMING_LIVE: ("🟢 直播中", "#66BB6A"),
            AppState.STREAMING_STANDBY: ("🟡 待机中 (备用视频)", "#FFA726"),
            AppState.STOPPING: ("🔴 停止中...", "#EF5350")
        }
        status_text, color = state_map.get(state, ("❓ 未知", "gray"))
        self.status_label.configure(text=status_text, text_color=color)

        if state == AppState.STREAMING_LIVE:
            self.source_label.configure(text=f"来源: {controller_ref.current_douyin_url}")
        elif state == AppState.STREAMING_STANDBY:
            self.source_label.configure(text=f"来源: {controller_ref.standby_video_path}")
        else:
            self.source_label.configure(text="来源: --")
            
        pid = controller_ref.ffmpeg.process.pid if controller_ref.ffmpeg.process else "--"
        self.ffmpeg_label.configure(text=f"FFmpeg PID: {pid}")

        broadcast_id = controller_ref.youtube.current_broadcast_id
        if broadcast_id:
             self.youtube_link_label.grid()
        else:
             self.youtube_link_label.grid_remove()


    def log_updater(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", message + "\n")
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except queue.Empty: pass
        finally: self.after(100, self.log_updater)

    def start_app(self):
        self.logger.log("▶️ 用户点击了【开始运行】按钮。")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.controller.start()

    def stop_app(self):
        self.logger.log("⏹️ 用户点击了【停止运行】按钮。")
        self.stop_button.configure(text="正在停止...", state="disabled")
        self.controller.stop()
        self.after(2000, lambda: [
            self.start_button.configure(state="normal"),
            self.stop_button.configure(text="🛑 停止运行")
        ])

    def open_youtube_link(self, event):
        """点击标签时，在浏览器中打开YouTube直播间。"""
        broadcast_id = self.controller.youtube.current_broadcast_id
        if broadcast_id:
            url = f"https://www.youtube.com/watch?v={broadcast_id}"
            self.logger.log(f"🔗 正在打开链接: {url}")
            webbrowser.open_new_tab(url)
            
    # ====================================================================
    #                      【BUG修复的关键】
    # ====================================================================
    def on_closing(self):
        """
        处理窗口关闭事件("X"按钮)，确保后台线程被干净地关闭。
        这是正确的实现方式。
        """
        self.logger.log("🚪 用户点击了窗口关闭按钮，正在执行清理操作...")
        
        # 1. 指挥控制器停止所有后台任务（包括FFmpeg和主循环）
        self.controller.stop()
        
        # 2. 销毁主窗口，这将自动结束 .mainloop()
        self.destroy()
