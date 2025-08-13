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
