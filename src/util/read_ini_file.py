# 编辑时间:2025/8/28 14:46 By Gwynliu7
import configparser

def read(file_path):
    config = configparser.ConfigParser()
    file = config.read(file_path, encoding='UTF-8')
    if not file:
        raise FileNotFoundError(f"无法读取配置文件：{file_path}")

    sections = config.sections()
    enable_create = config.get('monitor', 'enable_create') == "1"
    enable_delete = config.get('monitor', 'enable_delete') == "1"
    sync_empty_dir = config.get('sync', 'sync_empty_dir') == "1"

    return {'enable_create': enable_create, 'enable_delete': enable_delete, 'sync_empty_dir': sync_empty_dir}
