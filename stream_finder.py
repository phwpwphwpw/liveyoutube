# stream_finder.py (v2 - Streamlink Edition)
import streamlink
from streamlink.exceptions import PluginError, NoStreamsError

class StreamFinder:
    """负责从指定平台抓取直播源的URL (使用Streamlink核心)。"""

    def __init__(self, logger, config_manager):
        """
        初始化 StreamFinder。
        """
        self.logger = logger
        self.config = config_manager
        # Streamlink需要一个会话来管理插件和设置
        self.session = streamlink.Streamlink()
        # 设置必要的HTTP头，模拟浏览器访问，这是反屏蔽的关键
        self.session.set_option("http-headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Referer": "https://live.douyin.com/"
        })

    def get_douyin_stream_url(self, douyin_id: str) -> str | None:
        """
        使用Streamlink获取指定抖音ID的直播流地址。

        Args:
            douyin_id (str): 抖音用户ID。

        Returns:
            str | None: 如果找到，返回流地址；否则返回None。
        """
        url = f"https://live.douyin.com/{douyin_id}"
        self.logger.log(f"🕵️ [嗅探器] 正在使用 Streamlink 解析: {url}")

        try:
            # session.streams会返回一个包含所有可用清晰度流的字典
            streams = self.session.streams(url)
            
            if not streams:
                self.logger.log("⚠️ [嗅探器] 未找到任何直播流，主播可能未开播。")
                return None

            # 我们通常选择最高画质的流 'best'
            stream = streams["best"]
            self.logger.log("✅ [嗅探器] 成功获取到直播流地址！")
            return stream.url

        except NoStreamsError:
            self.logger.log("⚠️ [嗅探器] 未找到任何直播流 (NoStreamsError)，主播确定未开播。")
            return None
        except PluginError as e:
            # PluginError通常意味着平台更新了反爬机制，或者URL格式错误
            self.logger.log(f"❌ [嗅探器] Streamlink插件错误: {e}。可能是平台更新了防护策略。")
            return None
        except Exception as e:
            self.logger.log(f"❌ [嗅探器] 解析时发生未知错误: {e}")
            return None
