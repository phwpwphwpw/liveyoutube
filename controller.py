# controller.py
import threading
import time
from enum import Enum, auto

# 定义程序可能处于的几种状态
class AppState(Enum):
    IDLE = auto()               # 空闲或已停止
    INITIALIZING = auto()       # 初始化中 (获取YouTube推流码等)
    SCANNING = auto()           # 正在扫描抖音直播源
    STREAMING_LIVE = auto()     # 正在转推抖音直播
    STREAMING_STANDBY = auto()  # 正在推流本地备用视频 (故障转移)
    STOPPING = auto()           # 正在停止

class AppController:
    """应用程序的核心控制器，负责管理状态和业务逻辑流。"""

    def __init__(self, gui_instance, logger, config_manager, youtube_manager, ffmpeg_manager, stream_finder):
        self.gui = gui_instance
        self.logger = logger
        self.config = config_manager
        self.youtube = youtube_manager
        self.ffmpeg = ffmpeg_manager
        self.finder = stream_finder

        self.is_running = False
        self.main_thread = None
        self.current_state = AppState.IDLE
        self.state_handlers = {
            AppState.INITIALIZING: self._handle_initializing,
            AppState.SCANNING: self._handle_scanning,
            AppState.STREAMING_LIVE: self._handle_streaming_live,
            AppState.STREAMING_STANDBY: self._handle_streaming_standby,
        }
        
        self.douyin_ids = []
        self.current_douyin_url = None
        self.standby_video_path = None
        self.youtube_rtmp_url = None
        
    def start(self):
        """启动控制器主循环。"""
        if self.is_running:
            self.logger.log("⚠️ [控制器] 控制器已经在运行中。")
            return
        
        self.logger.log("🚀 [控制器] 收到启动指令，正在启动主控制线程...")
        self.is_running = True
        self.current_state = AppState.INITIALIZING
        self.main_thread = threading.Thread(target=self._run, daemon=True)
        self.main_thread.start()

    def stop(self):
        """停止控制器主循环。"""
        if not self.is_running:
            self.logger.log("ℹ️ [控制器] 控制器已经停止。")
            return
            
        self.logger.log("🛑 [控制器] 收到停止指令，正在优雅地关闭所有进程...")
        self.current_state = AppState.STOPPING
        self.is_running = False
        self.ffmpeg.stop_stream()
        if self.main_thread:
            self.main_thread.join(timeout=10)
            self.logger.log("✅ [控制器] 主控制线程已退出。")
        self.current_state = AppState.IDLE
        if self.gui: self.gui.update_status_display(self.current_state, self)


    def _run(self):
        """主循环，根据当前状态执行相应的处理函数。"""
        while self.is_running:
            if self.gui:
                self.gui.update_status_display(self.current_state, self)

            handler = self.state_handlers.get(self.current_state)
            if handler:
                next_state = handler()
                if self.current_state != next_state:
                    self.logger.log(f"🔀 [控制器] 状态切换: {self.current_state.name} -> {next_state.name}")
                    self.current_state = next_state
            elif self.current_state == AppState.STOPPING:
                break
            else:
                self.logger.log(f"❓ [控制器] 未知的状态: {self.current_state}，将切换到空闲状态。")
                time.sleep(1)
                self.current_state = AppState.IDLE

        self.logger.log("👋 [控制器] 主循环已结束。")
        
    def _handle_initializing(self):
        """初始化状态：获取所有必要的配置和YouTube推流信息。"""
        
        # ====================================================================
        #                      【BUG修复的关键】
        # ====================================================================
        raw_ids = self.config.get('Douyin', 'douyin_ids', []) # 默认获取空列表
        id_list = []
        # 判断 configobj 返回的是字符串还是列表
        if isinstance(raw_ids, str):
            id_list = raw_ids.split(',')
        elif isinstance(raw_ids, list):
            id_list = raw_ids
        
        # 清理列表，去除空项和多余的空格
        self.douyin_ids = [str(id).strip() for id in id_list if str(id).strip()]
        # ====================================================================

        self.standby_video_path = self.config.get('Douyin', 'standby_video_path')
        
        if not self.douyin_ids:
            self.logger.log("❌ [控制器] 致命错误：抖音ID列表为空，请在 yt.ini 中配置。")
            return AppState.STOPPING
            
        if not self.standby_video_path:
            self.logger.log("❌ [控制器] 致命错误：未配置备用视频路径，无法实现故障转移。")
            return AppState.STOPPING

        stream_id, self.youtube_rtmp_url = self.youtube.get_or_create_stream()
        if not self.youtube_rtmp_url:
            self.logger.log("❌ [控制器] 致命错误：无法从YouTube获取推流地址。")
            return AppState.STOPPING
        
        if not self.youtube.create_and_bind_broadcast(stream_id):
             self.logger.log("❌ [控制器] 致命错误：创建或绑定YouTube直播活动失败。")
             return AppState.STOPPING
        
        return AppState.SCANNING

    def _handle_scanning(self):
        """扫描状态：轮询抖音ID列表，寻找正在直播的源。"""
        for douyin_id in self.douyin_ids:
            if not self.is_running: return AppState.STOPPING
            
            self.current_douyin_url = self.finder.get_douyin_stream_url(douyin_id)
            if self.current_douyin_url:
                return AppState.STREAMING_LIVE
        
        return AppState.STREAMING_STANDBY

    def _handle_streaming_live(self):
        """推流直播状态：启动FFmpeg推流抖音源，并监控进程。"""
        process = self.ffmpeg.start_stream(self.current_douyin_url, self.youtube_rtmp_url, is_standby=False)
        
        if process:
            while self.is_running and process.poll() is None:
                time.sleep(2) 
            
            if not self.is_running: return AppState.STOPPING

            return AppState.STREAMING_STANDBY
        else:
            time.sleep(5) 
            return AppState.SCANNING

    def _handle_streaming_standby(self):
        """推流备用视频状态：循环推流本地视频，并定时在后台扫描新源。"""
        process = self.ffmpeg.start_stream(self.standby_video_path, self.youtube_rtmp_url, is_standby=True)
        
        if process:
            check_interval = int(self.config.get('Douyin', 'check_interval', 60))
            last_check_time = time.time()

            while self.is_running and process.poll() is None:
                if time.time() - last_check_time > check_interval:
                    for douyin_id in self.douyin_ids:
                        if not self.is_running: break
                        url = self.finder.get_douyin_stream_url(douyin_id)
                        if url:
                            self.current_douyin_url = url
                            self.ffmpeg.stop_stream()
                            return AppState.STREAMING_LIVE
                    last_check_time = time.time()
                time.sleep(1)

            if not self.is_running: return AppState.STOPPING

            return AppState.SCANNING
        else:
            self.logger.log("❌ [控制器] 启动备用视频推流失败！请检查视频文件路径和FFmpeg配置。")
            self.logger.log("🛑 [控制器] 这是一个严重错误，系统将停止运行。")
            return AppState.STOPPING
