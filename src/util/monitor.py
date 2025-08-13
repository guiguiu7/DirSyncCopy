# 编辑时间:2025/8/11 10:49
import time
import hashlib
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.util.log_config import log
import src.util.copy_util as cu

source = ""
dest = ""
file_list = []

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, exclude_patterns=None):
        self.exclude_patterns = exclude_patterns or [
            ".~", ".log", ".swp", ".swo",           # 临时文件和日志
            ".tmp", ".bak", ".sync", ".exe"         # 扩展常见文件后缀
        ]
        self.last_handled = {}  # 用于记录上次处理时间和MD5

    def should_ignore(self, file_path):
        for pattern in self.exclude_patterns:
            if pattern in file_path:  # 包含排除模式则忽略
                return True
            if file_path.startswith('.') and not file_path == '.':
                return True
        return False

    def on_modified(self, event):
        if event.is_directory:
            return
        if self.should_ignore(event.src_path):
            return

        # 事件去重：1秒内同一文件的多次修改只处理一次
        current_time = time.time()
        file_path = event.src_path
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return
        if file_path in self.last_handled:
            last_time, last_md5 = self.last_handled[file_path]
            if current_time - last_time < 0.5:  # 1秒内忽略重复事件
                return

        stored_md5 = None
        for item in file_list:
            if os.path.normpath(item["path"]) == os.path.normpath(file_path):
                stored_md5 = item["md5"]
                break
        current_md5 = cu._calculate_md5_large(file_path)
        if stored_md5 == current_md5:
            return
        self.last_handled[file_path] = (current_time, current_md5)
        log.info(f"文件修改: {file_path}")
        cu.compare_files(source, dest)

def run_monitor(watch_path, dest_path, files):
    global source,dest,file_list
    source = watch_path
    dest = dest_path
    file_list = files
    event_handle = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handle, watch_path, False)
    try:
        observer.start()
        log.info(f"开始监控: {watch_path}（按 Ctrl+C 停止）")
        # 无限循环保持程序运行
        while True:
            time.sleep(1)  # 减少CPU占用
    except KeyboardInterrupt:
        # 捕获用户中断（Ctrl+C）
        observer.stop()
        log.info("用户终止监控")
    except Exception as e:
        # 捕获其他异常并记录
        observer.stop()
        log.error(f"监控异常终止: {str(e)}", exc_info=True)
        raise  # 重新抛出异常，供外层处理
    finally:
        observer.join()