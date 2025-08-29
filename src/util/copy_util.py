# 编辑时间:2025/8/10 17:27
import hashlib
import os
import shutil
from pathlib import Path

from src.util.log_config import log

class Copy_Util:
    def __init__(self, source, dest, config):
        self.source = source
        self.dest = dest
        self.keep_empty_dir = config.get("sync_empty_dir")

    def _get_files(self, folder_path):
        files_info = []
        if not os.path.isdir(folder_path):
            raise Exception(f"目录不存在:{folder_path}")
        with os.scandir(folder_path) as files:
            for file in files:
                if file.name.startswith("~$") or file.name.startswith(".~") or os.path.splitext(file.name)[1] == ".exe":
                    continue
                if file.name.endswith((".log", ".ini")):
                    continue
                if file.is_file():
                    file_stat = file.stat()
                    file_info = {
                        'name': file.name,
                        'path': file.path,
                        'size': file_stat.st_size,  # 文件大小(字节)
                        'modified_time': file_stat.st_mtime,  # 最后修改时间(时间戳)
                        'created_time': file_stat.st_ctime,  # 创建时间(时间戳)
                        'is_dir': False,
                        'extension': os.path.splitext(file.name)[1],  # 文件扩展名
                        'md5': self._calculate_md5_large(file.path)
                    }
                    files_info.append(file_info)
                if file.is_dir():
                    subfolder_files = self._get_files(file.path)
                    files_info.extend(subfolder_files)
        files_info.sort(key=lambda x: (x["created_time"], x["name"]))
        return files_info

    def _get_dirs(self, root_dir):
        empty_folders = []
        root_path = Path(root_dir).resolve()  # 转换为绝对路径，处理相对路径

        if not root_path.exists():
            raise FileNotFoundError(f"目录不存在: {root_path}")

        if not root_path.is_dir():
            raise NotADirectoryError(f"不是目录: {root_path}")

        # 遍历目录树
        for dirpath, dirnames, filenames in os.walk(root_path):
            if not dirnames and not filenames:
                empty_folders.append(str(Path(dirpath).resolve()))

        return empty_folders

    def _calculate_md5_large(self, file_path, block_size=65536):
        """计算大文件的MD5哈希值（分块读取）"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                md5.update(block)
        return md5.hexdigest()


    def compare_files(self):
        result = {}
        source_files = []
        dest_files = []
        copy_source_files = []
        source_dirs = []
        dest_dirs = []
        try:
            # 添加源目录文件列表
            source_files = self._get_files(self.source)
            result["source_files"] = source_files
            # 添加目标目录文件列表
            dest_files = self._get_files(self.dest)
            result["dest_files"] = dest_files

            # 获取空目录
            if self.keep_empty_dir:
                source_dirs = self._get_dirs(self.source)
                result["source_dirs"] = source_dirs
                dest_dirs = self._get_dirs(self.dest)
                result["dest_dirs"] = dest_dirs

        except Exception as e:
            raise
        copy_source_files = source_files.copy()
        result["copy_source_files"] = copy_source_files
        # 获取需要的同步文件
        same_num, copy_num = self.sync_files(source_files, dest_files)

        log.info(f"相同的文件有{same_num}个")
        if copy_num:
            log.info(f"需要拷贝的文件有{copy_num}个")
        self._source_to_dest(source_files)
        return_files = []
        for file in source_files.copy():
            file_info = {
                'name': file["name"],
                'path': file["path"],
                'is_dir': file["is_dir"],
                'md5': file["md5"]
            }
            return_files.append(file_info)
        result["return_files"] = return_files

        # 同步空目录
        if self.keep_empty_dir:
            if not result.get("source_dirs"):
                return result
            empty_dirs = self.sync_empty_dirs(source_dirs, dest_dirs)
            if empty_dirs['processed']:
                log.info(f"成功同步{empty_dirs.get('processed')}个空文件夹")
                log.info(f"成功同步空文件夹：{empty_dirs.get('result')}")

        return result


    def sync_files(self, source_files, dest_files):
        """
        文件同步逻辑：
            1. 使用字典加速查找
            2. 减少嵌套循环
            3. 添加错误处理
            4. 使用pathlib处理路径

        Args:
            source_files []: 源目录文件
            dest_files []: 目标目录文件
        Return:
            processed : 相同文件的数量
            len(source_files) : 复制的文件数量
        """
        # 构建目标文件MD5索引 {md5: [file_info]}
        dest_md5_index = {}
        for df in dest_files:
            dest_md5_index.setdefault(df["md5"], []).append(df)

        processed = 0
        for sf in source_files.copy():  # 遍历副本以便修改原列表
            if sf["md5"] not in dest_md5_index:  # 跳过MD5不同的文件 需要复制的文件
                continue

            # MD5 相同且名字相同 移除相同的文件，不需要复制
            same_name = any(
                df["name"] == sf["name"] for df in dest_md5_index[sf["md5"]]
            )

            if same_name:
                processed += 1
                source_files.remove(sf)
                continue

            # 处理MD5相同名字不同的文件
            for df in dest_md5_index[sf["md5"]]:
                try:
                    dest_path = Path(df["path"])
                    source_path = Path(sf["path"])
                    if not (Path(sf["path"]).parent == Path(df["path"]).parent):
                        break
                    if os.path.exists(dest_path):
                        os.unlink(dest_path)
                        shutil.copy2(source_path, dest_path.parent)
                        log.info(
                            f"文件重命名: {sf['path']} -> {df['path']} "
                            f"(MD5: {sf['md5'][:8]}...)"
                        )
                        processed += 1
                        source_files.remove(sf)
                        break
                except OSError as e:
                    log.error(f"移动文件失败: {df['path']} -> {sf['path']} | 错误: {e}")

        return processed, len(source_files)

    def sync_empty_dirs(self, source_dirs, dest_dirs):
        """
        同步空文件夹
        :param source_dirs:
        :param dest_dirs:
        :return:
        """
        copy_source_dirs = []
        for dir in source_dirs:
            source_dir_relative = Path(dir).relative_to(self.source)
            dest_dir = self.dest / source_dir_relative
            if dest_dir.exists() and dest_dir.is_dir():
                continue
            copy_source_dirs.append(dir)
            os.makedirs(dest_dir)
        return {"processed": len(copy_source_dirs), "result": copy_source_dirs}

    def _source_to_dest(self, need_copy_files):
        """
        将文件复制到目标目录
        :arg
            need_copy_files []: 需要复制的文件列表
        :return 复制的文件数量
        """
        n = 0
        if not need_copy_files:
            # log.info("没有需要复制的文件")
            return n

        os.makedirs(self.dest, exist_ok=True)

        for file_info in need_copy_files:
            # 1. 获取源文件完整路径
            source_file_path = file_info['path']

            # 2. 计算相对路径（核心：保留源目录结构）
            # 例如：source为"a/b"，文件为"a/b/c/d.txt"，相对路径为"c/d.txt"
            relative_path = os.path.relpath(source_file_path, self.source)

            # 3. 构建目标文件完整路径
            target_file_path = os.path.join(self.dest, relative_path)

            # 4. 创建目标文件所在的父目录（自动创建多级目录）
            target_file_dir = os.path.dirname(target_file_path)
            os.makedirs(target_file_dir, exist_ok=True)

            # 5. 复制文件（保留元数据）
            shutil.copy2(source_file_path, target_file_path)
            n += 1
            log.info(f"成功复制: {source_file_path} -> {target_file_path}")

        log.info(f"成功复制 {n}/{len(need_copy_files)} 个文件")
        return n
