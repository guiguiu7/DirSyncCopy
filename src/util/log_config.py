# log_config.py
import logging

def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("monitor.log"),  # 日志写入文件
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    return logging.getLogger(__name__)

# 创建全局logger实例
log = setup_logging()