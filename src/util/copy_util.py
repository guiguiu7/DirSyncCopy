# 编辑时间:2025/8/10 17:27
import hashlib
import os
import shutil

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
    n = 0
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
    for source_file in source_files.copy():
        for dest_file in dest_files:
            if (source_file["name"] == dest_file["name"] and
                    source_file["md5"] == dest_file["md5"]):
                n += 1
                source_files.remove(source_file)
                break
    log.info(f"相同的文件有{n}个")
    log.info(f"需要拷贝的文件有{len(source_files)}个")
    _source_to_dest(source_files)
    return result


def _source_to_dest(need_copy_files):
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
