# ffmpeg_manager.py (v4 - Keyframe Optimization Edition)
import subprocess
import time

class FFmpegManager:
    """负责构建和管理FFmpeg推流进程，具有更健壮的参数配置和代理支持。"""

    def __init__(self, logger, config_manager):
        self.logger = logger
        self.config = config_manager
        self.process = None

    def start_stream(self, stream_input: str, youtube_rtmp_url: str, is_standby: bool = False) -> subprocess.Popen | None:
        ffmpeg_path = self.config.get('FFmpeg', 'ffmpeg_path', 'ffmpeg')
        preferences = self.config.get('FFmpeg', 'encoder_preference', 'copy,nvenc,cpu').split(',')

        base_cmd = [ffmpeg_path, "-hide_banner"]
        if is_standby or 'http' not in stream_input:
            base_cmd.extend(["-re"])
        if is_standby:
            base_cmd.extend(["-stream_loop", "-1"])
        
        base_cmd.extend(["-i", stream_input])

        for encoder in preferences:
            encoder = encoder.strip().lower()
            cmd = list(base_cmd)
            encoder_name = ""

            if encoder == 'copy' and not is_standby:
                encoder_name = "直通 (Copy)"; cmd.extend(["-c:v", "copy"])
            elif encoder == 'nvenc':
                encoder_name = "NVIDIA NVENC"; preset = self.config.get_section('FFmpeg').get('nvenc_preset', 'p5'); cmd.extend(["-c:v", "h264_nvenc", "-preset", preset])
            elif encoder == 'qsv':
                encoder_name = "Intel QSV"; preset = self.config.get_section('FFmpeg').get('qsv_preset', 'fast'); cmd.extend(["-c:v", "h264_qsv", "-preset", preset])
            elif encoder == 'cpu':
                encoder_name = "CPU (libx264)"; preset = self.config.get_section('FFmpeg').get('cpu_preset', 'veryfast'); threads = self.config.get_section('FFmpeg').get('cpu_threads', '4'); cmd.extend(["-c:v", "libx264", "-preset", preset, "-threads", threads, "-pix_fmt", "yuv420p"])
            else:
                if encoder == 'copy' and is_standby: self.logger.log("ℹ️ [FFmpeg] 备用视频推流跳过 'copy' 选项，因其需要重新编码以循环。")
                continue

            audio_codec = self.config.get('FFmpeg', 'c_a', 'copy')
            if audio_codec == 'copy' and not is_standby:
                 cmd.extend(["-c:a", "copy"])
            else:
                cmd.extend(["-c:a", "aac"]); audio_bitrate = self.config.get('FFmpeg', 'b_a', '128k')
                if audio_bitrate: cmd.extend(["-b:a", audio_bitrate])
                cmd.extend(["-ar", "44100"])

            # --- 视频码率和其他参数 (仅在重编码时应用) ---
            if encoder != 'copy':
                bitrate = self.config.get('FFmpeg', 'bitrate', '4000k')
                if bitrate: cmd.extend(["-b:v", bitrate, "-maxrate", bitrate, "-bufsize", "8000k"])
                
                # ====================================================================
                #                      【最终修复的关键】
                # ====================================================================
                # 强制设定关键帧间隔 (GOP size)。YouTube推荐2-4秒。
                # 对于60fps的视频，120帧就是2秒一个关键帧，非常理想。
                # 这是一个对直播流非常重要的参数。
                cmd.extend(["-g", "120"])
                # ====================================================================

            cmd.extend(["-f", "flv", youtube_rtmp_url])

            proxy_url = self.config.get('Proxy', 'proxy_url')
            if proxy_url:
                self.logger.log(f"✅ [FFmpeg] 检测到代理设置，正在为推流添加代理参数: {proxy_url}")
                cmd.extend(["-rtmp_proxy", proxy_url])

            self.logger.log(f"🚀 [FFmpeg] 正在尝试使用 [{encoder_name}] 模式启动推流...")
            self.logger.log(f"   -> 执​​行的命令: {' '.join(cmd)}")

            try:
                self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                time.sleep(5)
                if self.process.poll() is None:
                    self.logger.log(f"✅ [FFmpeg] 使用 [{encoder_name}] 成功启动进程！PID: {self.process.pid}")
                    return self.process
                else:
                    error_output = self.process.stderr.read(); self.logger.log(f"❌ [FFmpeg] 使用 [{encoder_name}] 启动失败。FFmpeg 错误: {error_output}"); self.process = None
            except FileNotFoundError: self.logger.log(f"❌ [FFmpeg] 严重错误：找不到 FFmpeg 程序！请检查路径配置: '{ffmpeg_path}'"); return None
            except Exception as e: self.logger.log(f"❌ [FFmpeg] 启动时发生未知异常: {e}"); return None

        self.logger.log("❌ [FFmpeg] 所有编码器都尝试失败，无法启动推流。"); return None

    def stop_stream(self):
        if self.process and self.process.poll() is None:
            self.logger.log(f"🔪 [FFmpeg] 正在终止进程 PID: {self.process.pid}...")
            try:
                self.process.kill(); self.process.wait(timeout=5)
                self.logger.log("✅ [FFmpeg] 进程已成功终止。")
            except subprocess.TimeoutExpired: self.logger.log("⚠️ [FFmpeg] kill后等待超时，进程可能未完全清理。")
            except Exception as e: self.logger.log(f"❌ [FFmpeg] 终止进程时发生错误: {e}")
        self.process = None
