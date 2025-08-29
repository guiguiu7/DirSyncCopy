# 编辑时间:2025/8/8 18:34 By Gwynliu7
import os.path
import sys
import platform

import src.util.copy_util as cu
import src.util.monitor as monitor
import src.util.read_ini_file as rif
from src.util.log_config import log


def print_help():
    """显示帮助信息"""
    print("文件同步工具")
    print("命令行用法: DirSyncCopy.exe [[选项] | [源目录路径] [目标路径]]")
    print("选项:")
    print("  -h, --help    显示此帮助信息")
    print("  -v, --version 显示版本信息")
    print("\n例:")
    print("DirSyncCopy.exe -h")
    print("DirSyncCopy.exe source_path dest_path")
    print("DirSyncCopy.exe dest_path")
    print("\n如果未指定目录路径，默认监控当前目录为源目录路径")
    print("\n额外配置需在同目录中的config.ini中配置\n")


def print_version():
    """显示版本信息"""
    print("文件监控工具 v1.0")


def get_effective_path(path):
    if '"' in path:
        path = path.replace('"', '')
    if not os.path.exists(path):
        raise FileNotFoundError(f"目录不存在{path}")
    abs_path = os.path.abspath(path)
    normalized_path = os.path.normpath(abs_path)
    return normalized_path


if __name__ == "__main__":
    source = ""
    dest = ""
    # 处理命令行参数
    if len(sys.argv) == 1:  # 双击直接运行
        print_help()
        source = input("手动输入源目录(可不填): ")
        dest = input("手动输入目标目录: ")
        if not source:
            source = get_effective_path(".")
    elif len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print_help()
            sys.exit(0)
        elif sys.argv[1] in ["-v", "--version"]:
            print_version()
            sys.exit(0)
        elif len(sys.argv) >= 3:
            source = sys.argv[1]
            dest = sys.argv[2]
        else:
            dest = sys.argv[1]
            source = "."  # 当前目录
    if not source or not dest:
        log.error("错误：路径不能为空！")
        os.system("pause")
        sys.exit(1)
    try:
        source = get_effective_path(source)
        dest = get_effective_path(dest)
        if platform.system() == "Windows":
            source = source.lower()
            dest = dest.lower()
        if source == dest:
            raise Exception("源目录与目标目录不能相同")
    except Exception as e:
        log.error(e)
        os.system("pause")
        sys.exit(1)

    # 读取配置文件
    config = {}
    try:
        config = rif.read(f"{source}/config.ini")
    except Exception as e:
        log.error(e)
        sys.exit(0)

    # 程序一运行会先进行文件的比对复制
    log.info(f"源文件目录:{source}")
    log.info(f"目标目录:{dest}")
    files = cu.Copy_Util(source, dest, config).compare_files()
    if files.get('source_files') != None:
        log.info(f"需要同步的文件:{'无' if files.get('source_files') == [] else files.get('source_files')}")
    # 自动重启机制：如果程序崩溃，等待几秒后重新启动
    while True:
        try:
            monitor.run_monitor(source, dest, files.get('copy_source_files'), config)
            break  # 如果正常退出（如用户Ctrl+C），则终止循环
        except Exception as e:
            log.warning(f"程序异常，将在 5 秒后重启...{e}")
            time.sleep(5)  # 等待5秒后重启
