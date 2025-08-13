# liveyoutube
youtube直播 仍有bug
 **7x24 小时无人值守的、具备故障转移能力的自动化直播解决方案**。采用模块化的设计思想，将复杂的系统拆解为一系列高内聚、低耦合的组件。这样做的好处是代码清晰、易于维护，并且未来扩展新功能（例如支持更多直播平台）会变得非常简单。

-----

### **项目架构设计 (Architecture)**

我将把项目分为以下几个核心模块，每个模块都是一个独立的 `.py` 文件，各司其职：

1.  **`main.py` - 程序入口 (Entry Point)**

      * 职责：初始化应用程序，启动主控制器，是整个程序的起点。

2.  **`config_manager.py` - 配置管理器**

      * 职责：专门负责加载、解析和验证 `yt.ini` 配置文件。提供一个全局的、唯一的配置访问点。

3.  **`gui_app.py` - 图形用户界面**

      * 职责：构建基于 `customtkinter` 的用户界面，负责展示日志、状态，并响应用户的操作（开始/停止）。它将与主控制器进行通信。

4.  **`youtube_manager.py` - YouTube API 封装**

      * 职责：封装所有与 YouTube Data API v3 的交互，包括身份验证、创建/获取直播活动、获取推流地址等。

5.  **`ffmpeg_manager.py` - FFmpeg 进程管理器**

      * 职责：根据配置动态构建 FFmpeg 命令，并负责启动、监控和终止 FFmpeg 子进程。

6.  **`stream_finder.py` - 直播源嗅探器**

      * 职责：核心的直播源获取模块。目前它将实现基于 Playwright 的抖音直播源抓取逻辑。

7.  **`controller.py` - 核心控制器 (大脑)**

      * 职责：这是整个系统的大脑和心脏。它将以状态机的模式运行，负责整个业务逻辑的流转：扫描直播 -\> 推送直播 -\> 检测故障 -\> 切换到备用视频 -\> 寻找新源 -\> 恢复直播。它将调度其他所有模块来完成工作。

8.  **`logger.py` - 日志系统**

      * 职责：提供一个统一的日志记录接口，能将日志信息同时输出到控制台和GUI界面。

9.  **`yt.ini` - 配置文件**

      * 职责：存储所有可配置的参数，让用户无需修改代码即可调整系统行为。

-----

### **第一步：项目文件结构与依赖**

以下文件结构：


/youtube_restream_bot/
|-- main.py
|-- gui_app.py
|-- controller.py
|-- config_manager.py
|-- youtube_manager.py
|-- ffmpeg_manager.py
|-- stream_finder.py
|-- logger.py
|-- yt.ini
|-- requirements.txt


 `requirements.txt` 文件，内容如下。这是我项目的所有依赖。

**`requirements.txt`**

txt
customtkinter
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
playwright
configobj


可以通过 `pip install -r requirements.txt` 来安装所有依赖。
同时，Playwright 需要安装浏览器驱动，请在命令行运行：`playwright install`

-----

### **第二步：实现 (Coding)**

。。。。。。。。。。。。。。。。。。。。。。。。。。。。

#### **1. `yt.ini` (配置文件)**

这是我系统的“控制面板”。相比以前的版本，做了一些优化，增加了**多房间ID轮询**和**备用视频**的配置。

ini
[Douyin]
  # 要轮询的抖音主播ID列表，用英文逗号分隔。脚本会按顺序扫描。
  douyin_ids = MS4wLjABAAAAxxxxxxxx1,MS4wLjABAAAAxxxxxxxx2

  # 本地备用视频文件的完整路径。当所有主播都未开播时，将循环推流此视频。
  # 请使用正斜杠 / 作为路径分隔符，例如 C:/videos/standby.mp4
  standby_video_path = 

  # 使用浏览器打开抖音页面后，等待页面加载并抓取到直播地址的时间（秒）。
  wait_time = 15

  # 当主播未开播时，脚本会每隔这个设定的时间（秒）就去检查一次。
  check_interval = 60


[YouTube]
  # 授权后生成的凭证文件名，应与脚本放在同一目录或提供完整路径。
  client_secret_file = client_secret.json

  # YouTube直播的标题。
  broadcast_title = 24/7 Live Stream | Powered by Test
  
  # YouTube直播的描述。
  broadcast_description =  This is a 24/7 live stream.
  
  # 分类ID: 22=人物与博客, 26=方法与时尚, 24=娱乐, 20=游戏
  category_id = 24
  
  # 隐私状态: public, private, unlisted
  privacy_status = public
  
  # 是否允许YouTube在检测到推流信号后自动开始直播。
  enable_auto_start = true

  # 是否允许YouTube在推流信号中断后自动结束直播 (重要：在我的方案中设为 false)。
  # 我不希望YouTube自动结束，因为我的脚本会快速恢复推流。
  enable_auto_stop = false


[FFmpeg]
  # ffmpeg.exe 程序的路径。如果已在环境变量中，写`ffmpeg`即可。
  ffmpeg_path = ffmpeg

  # 推送到YouTube的视频码率。例如: 4000k
  bitrate = 4000k
  
  # 核心：编码器使用优先级，用逗号分隔。脚本会从左到右依次尝试。
  # 可用值: copy (直接复制), qsv (Intel核显), nvenc (NVIDIA显卡), cpu (CPU软件编码)
  encoder_preference = copy,nvenc,qsv,cpu
  
  # 音频编码器: copy = 直接复制, aac = 重新编码为AAC
  audio_codec = copy
  
  # 音频码率 (仅在 audio_codec 不是 copy 时有效)。例如 128k
  audio_bitrate = 128k
  
  # --- 各种编码器的预设参数 ---
  nvenc_preset = p5
  qsv_preset = fast
  cpu_preset = veryfast
  cpu_threads = 4


[System]
  # Playwright使用的浏览器路径 (可选，留空则使用默认安装的)。
  browser_path = 

  # 系统代理设置。留空则不使用代理。格式: http://127.0.0.1:7890
  proxy_url = 



#### **2. `logger.py` (日志系统)**

一个简单的日志分发器，用于解耦日志来源和输出目的地。

python
# logger.py
import queue
import time

class UILogger:
    """一个简单的日志记录器，将日志消息放入队列中以供GUI线程安全地消费。"""
    def __init__(self, log_queue: queue.Queue):
        self.log_queue = log_queue

    def log(self, message: str):
        """
        记录一条日志消息。

        Args:
            message (str): 要记录的消息。
        """
        timestamp = time.strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        # 放入队列，让GUI线程来处理实际的显示
        self.log_queue.put(log_entry)
        # 同时打印到控制台，方便调试
        print(log_entry)



#### **3. `config_manager.py` (配置管理器)**

使用`ConfigObj`库来加载和访问配置，可以保留注释，非常友好。

python
# config_manager.py
import os
from configobj import ConfigObj

class ConfigManager:
    """负责加载、访问和验证 yt.ini 配置文件。"""
    def __init__(self, logger, config_path='yt.ini'):
        self.logger = logger
        self.config_path = config_path
        self.config = None
        self.load_config()

    def load_config(self):
        """加载配置文件，如果不存在则记录错误。"""
        if not os.path.exists(self.config_path):
            self.logger.log(f"❌ 错误：配置文件 '{self.config_path}' 不存在！")
            self.config = ConfigObj() # 创建一个空的，避免后续调用出错
        else:
            try:
                self.config = ConfigObj(self.config_path, encoding='UTF8', indent_type='  ')
                self.logger.log(f"✅ 配置文件 '{self.config_path}' 加载成功。")
            except Exception as e:
                self.logger.log(f"❌ 加载配置文件 '{self.config_path}' 时出错: {e}")
                self.config = ConfigObj()

    def get(self, section, key, default=None):
        """
        从配置中获取一个值。

        Args:
            section (str): 配置中的节名。
            key (str): 配置中的键名。
            default: 如果找不到值，返回的默认值。

        Returns:
            返回找到的值或默认值。
        """
        try:
            return self.config[section][key]
        except KeyError:
            self.logger.log(f"⚠️ 警告：在配置文件的 [{section}] 中未找到 '{key}'。将使用默认值: {default}。")
            return default

    def get_section(self, section):
        """获取整个节。"""
        return self.config.get(section, {})


