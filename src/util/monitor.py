# 编辑时间:2025/8/11 10:49
import time
import hashlib
import os
import shutil

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.util.log_config import log
import src.util.copy_util as cu

source = ""
dest = ""

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_list, exclude_patterns=None, enable_create=True, enable_delete=True):
        self.exclude_patterns = exclude_patterns or [
            ".~", ".log", ".swp", ".swo",           # 临时文件和日志
            ".tmp", ".bak", ".sync", ".exe"         # 扩展常见文件后缀
        ]
        self.last_handled = {}  # 用于记录上次处理时间和MD5
        self.file_list = file_list
        self.enable_delete = enable_delete
        self.enable_create = enable_create

    def should_ignore(self, file_path):
        for pattern in self.exclude_patterns:
            if pattern in file_path:  # 包含排除模式则忽略
                return True
            if file_path.startswith('.') and not file_path == '.':
                return True
        return False

    def on_created(self, event):
        # 只处理目录创建事件（on_modified可能触发多次，on_created更精准）
        if self.enable_create:
            self._sync_create(event.src_path)

    def on_deleted(self, event):
        """处理目录删除，同步删除目标目录对应文件夹"""
        if self.enable_delete:
            self._sync_deleted(event.src_path)

    def _sync_deleted(self, path):
        """删除目标目录中对应的文件夹"""
        try:
            relative_dir = Path(path).relative_to(source)
        except ValueError:
            return  # 不在源目录下，忽略

        dest_path = dest / relative_dir
        if not dest_path.exists():
            return
        if dest_path.is_dir():
            try:
                # 递归删除目录（包括所有子文件和子目录）
                shutil.rmtree(dest_path)
                log.info(f"删除目录：{dest_path}")
            except Exception as e:
                log.error(f"删除目录失败：{dest_path}，错误：{e}")
        else:
            os.unlink(dest_path)
            log.info(f"删除文件：{dest_path}")

    def _sync_create(self, path):
        # 检查是否是源目录下的子目录
        try:
            # 获取相对于源目录的相对路径（如 source/sub/dir → sub/dir）
            relative_path = Path(path).relative_to(source)
        except ValueError:
            # 不在源目录下，忽略
            return

        # 目标目录中对应的路径
        dest_path = dest / relative_path

        # 若目标目录不存在，则创建（包括所有父目录）
        if not dest_path.exists() and Path(path).is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
            log.info(f"同步创建目录：{dest_dir}")
        elif not dest_path.exists() and Path(path).is_file():
            shutil.copy2(path, dest_path)
            log.info(f"同步创建文件：{dest_path}")
        else:
            log.warn(f"已存在：{dest_path}")

    def on_modified(self, event):
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
        for item in self.file_list:
            if os.path.normpath(item["path"]) == os.path.normpath(file_path):
                stored_md5 = item["md5"]
                break
        current_md5 = cu._calculate_md5_large(file_path)
        if stored_md5 == current_md5:
            return
        self.last_handled[file_path] = (current_time, current_md5)
        log.info(f"文件修改: {file_path}")
        self.file_list = cu.compare_files(source, dest)[2]

def run_monitor(watch_path, dest_path, files):
    global source,dest,file_list
    source = watch_path
    dest = dest_path
    event_handle = FileChangeHandler(files)
    observer = Observer()
    observer.schedule(event_handle, watch_path, True)
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