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
