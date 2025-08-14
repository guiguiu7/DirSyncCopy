# 编辑时间:2025/8/10 17:27
import hashlib
import os
import shutil
from pathlib import Path

from src.util.log_config import log

source = ""
dest = ""


def _get_files(folder_path):
    files_info = []
    if not os.path.isdir(folder_path):
        raise Exception(f"文件夹路径不存在:{folder_path}")
    for file_name in os.listdir(folder_path):
        if file_name.startswith("~$") or file_name.startswith(".~") or os.path.splitext(file_name)[1] == ".exe":
            continue
        if ".log" in file_name:
            continue
        file = os.path.join(folder_path, file_name)
        if os.path.isfile(file):
            file_info = {
                'name': file_name,
                'path': os.path.normpath(file),
                'size': os.path.getsize(file),  # 文件大小(字节)
                'modified_time': os.path.getmtime(file),  # 最后修改时间(时间戳)
                'created_time': os.path.getctime(file),  # 创建时间(时间戳)
                'is_dir': False,
                'extension': os.path.splitext(file_name)[1],  # 文件扩展名
                'md5': _calculate_md5_large(file)
            }
            files_info.append(file_info)
    files_info.sort(key=lambda x: (x["created_time"], x["name"]))
    return files_info


def _calculate_md5_large(file_path, block_size=65536):
    """计算大文件的MD5哈希值（分块读取）"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            md5.update(block)
    return md5.hexdigest()


def compare_files(source, destination):
    global dest
    dest = destination
    result = []
    source_files = []
    dest_files = []
    copy_source_files = []
    try:
        # 添加源目录文件列表
        source_files = _get_files(source)
        result.append(source_files)
        # 添加目标目录文件列表
        dest_files = _get_files(destination)
        result.append(dest_files)
    except Exception as e:
        raise
    copy_source_files = source_files.copy()
    result.append(copy_source_files)
    # 获取需要的同步文件
    same_num, copy_num = sync_files(source_files, dest_files)

    log.info(f"相同的文件有{same_num}个")
    if copy_num:
        log.info(f"需要拷贝的文件有{copy_num}个")
    _source_to_dest(source_files)
    return result


def sync_files(source_files, dest_files):
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


def _source_to_dest(need_copy_files):
    """
    将文件复制到目标目录
    :arg
        need_copy_files []: 需要复制的文件列表
    :return 复制的文件数量
    """
    n = 0
    if not need_copy_files:
        log.info("没有需要复制的文件")
        return n
    os.makedirs(dest, exist_ok=True)
    for file in need_copy_files:
        shutil.copy2(file["path"], dest)
        n += 1
        log.info(f"成功复制:{file['name']}")
    log.info(f"成功复制 {n}/{len(need_copy_files)} 个文件")
    return n
