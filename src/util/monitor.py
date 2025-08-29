# 编辑时间:2025/8/11 10:49 By Gwynliu7
import sys
import time
import hashlib
import os
import shutil

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.util.log_config import log
import src.util.copy_util as cu
import src.util.read_ini_file as rif

source = ""
dest = ""

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_list, config, exclude_patterns=None, enable_create=True, enable_delete=True):
        self.exclude_patterns = exclude_patterns or [
            ".~", ".log", ".swp", ".swo",           # 临时文件和日志
            ".tmp", ".bak", ".sync", ".exe", ".ini"         # 扩展常见文件后缀
        ]
        self.last_handled = {}  # 用于记录上次处理时间和MD5
        self.file_list = file_list
        self.enable_delete = config.get("enable_delete")       # 配置是否监控删除
        self.enable_create = config.get("enable_create")       # 配置是否监控创建

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

    def on_moved(self, event):
        if event.is_directory and not event.is_synthetic:
            # 构建源目录和目标目录的路径对象
            src_dir = Path(event.src_path)
            dest_dir = dest / src_dir.relative_to(source)

            # 新的目标路径（根据新名称）
            new_dest_dir = dest / Path(event.dest_path).relative_to(source)

            try:
                # 如果目标目录已存在则先删除
                if new_dest_dir.exists():
                    shutil.rmtree(new_dest_dir)

                # 重命名目标目录
                if dest_dir.exists():  # 确保源目录存在
                    shutil.move(str(dest_dir), str(new_dest_dir))
                    print(f"文件夹已重命名: {dest_dir} -> {new_dest_dir}")

            except PermissionError:
                print(f"权限不足，无法重命名文件夹: {dest_dir}")
            except Exception as e:
                print(f"重命名文件夹时出错: {str(e)}")

    def on_deleted(self, event):
        """处理目录删除，同步删除目标目录对应文件夹"""
        if self.enable_delete:
            self._sync_deleted(event.src_path)

    def _sync_deleted(self, path):
        print("delete")
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
                log.info(f"同步删除目录：{dest_path}")
            except Exception as e:
                log.error(f"同步删除目录失败：{dest_path}，错误：{e}")
        else:
            os.unlink(dest_path)
            log.info(f"同步删除文件：{dest_path}")

    def _sync_create(self, path):
        print("create")
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
            log.info(f"同步创建目录：{dest_path}")
        elif not dest_path.exists() and Path(path).is_file():
            shutil.copy2(path, dest_path)
            log.info(f"同步创建文件：{dest_path}")
        else:
            log.warn(f"已存在：{dest_path}")

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
        for item in self.file_list:
            if os.path.normpath(item["path"]) == os.path.normpath(file_path):
                stored_md5 = item["md5"]
                break

        copy_util = cu.Copy_Util(source, dest)
        current_md5 = copy_util._calculate_md5_large(file_path)
        if stored_md5 == current_md5:
            return
        self.last_handled[file_path] = (current_time, current_md5)
        log.info(f"文件修改: {file_path}")
        self.file_list = copy_util.compare_files(source, dest)[2]

def run_monitor(watch_path, dest_path, files, config):
    global source,dest,file_list
    source = watch_path
    dest = dest_path
    event_handle = FileChangeHandler(files, config)
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