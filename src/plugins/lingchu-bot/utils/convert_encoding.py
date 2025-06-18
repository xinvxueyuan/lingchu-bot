import os
import codecs
import argparse

def detect_encoding(file_path):
    """尝试用常见编码检测文件编码"""
    encodings_to_try = [
        'utf-8',
        'gb2312',
        'gbk',
        'big5',
        'utf-16',
        'utf-16le',
        'utf-16be',
        'ascii'
    ]
    
    for encoding in encodings_to_try:
        try:
            with codecs.open(file_path, 'r', encoding=encoding) as f:
                f.read()
                return encoding
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    
    return None

def convert_encoding(file_path, source_encoding=None, target_encoding='utf-8'):
    """将文件转换为指定编码"""
    try:
        # 如果没有指定编码，则尝试自动检测
        if source_encoding is None:
            source_encoding = detect_encoding(file_path)
            if source_encoding is None:
                print(f"无法确定编码，跳过: {file_path}")
                return False
        
        # 读取原始文件
        with codecs.open(file_path, 'r', encoding=source_encoding) as f:
            content = f.read()
        
        # 写入目标编码
        with codecs.open(file_path, 'w', encoding=target_encoding) as f:
            f.write(content)
        
        print(f"成功转换({source_encoding} -> {target_encoding}): {file_path}")
        return True
    
    except UnicodeDecodeError:
        print(f"解码失败(尝试使用 {source_encoding}): {file_path}")
        return False
    except Exception as e:
        print(f"处理失败({str(e)}): {file_path}")
        return False

def process_target(target, extension=None, force_encoding=None, target_encoding='utf-8'):
    """处理目标路径（可以是文件或目录）"""
    if os.path.isfile(target):
        # 如果是单个文件
        if extension is None or target.lower().endswith(extension.lower()):
            convert_encoding(target, force_encoding, target_encoding)
    elif os.path.isdir(target):
        # 如果是目录
        if extension is None:
            print("错误：处理目录时必须指定文件扩展名")
            return
        
        for root, dirs, files in os.walk(target):
            for file in files:
                if file.lower().endswith(extension.lower()):
                    file_path = os.path.join(root, file)
                    convert_encoding(file_path, force_encoding, target_encoding)
    else:
        print(f"错误：路径不存在 '{target}'")

def interactive_mode():
    """交互模式"""
    print("文件编码转换工具(多种编码 -> 目标编码)")
    
    # 获取用户输入的目标路径
    target = input("请输入要处理的文件或目录路径: ").strip()
    if not target:
        target = os.path.dirname(os.path.abspath(__file__))
    
    # 如果是目录，需要获取文件扩展名
    extension = None
    if os.path.isdir(target):
        extension = input("请输入要处理的文件扩展名(例如: .dc 或 .txt): ").strip()
        if not extension.startswith('.'):
            extension = '.' + extension
    
    # 询问目标编码
    target_encoding = input("请输入目标编码(默认utf-8): ").strip().lower() or 'utf-8'
    
    # 询问是否强制使用特定编码
    force_encoding = None
    use_auto = input("是否自动检测源编码?(y/n, 默认y): ").strip().lower()
    if use_auto not in ('y', ''):
        force_encoding = input("请输入要强制使用的源编码(例如: gb2312, gbk, big5): ").strip().lower()
    
    print(f"\n开始转换目标 '{target}'...")
    process_target(target, extension, force_encoding, target_encoding)
    print("\n转换完成!")

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='文件编码转换工具(多种编码 -> 目标编码)')
    parser.add_argument('-t', '--target', help='要处理的文件或目录路径')
    parser.add_argument('-e', '--extension', help='要处理的文件扩展名(处理目录时需要)')
    parser.add_argument('-f', '--force-encoding', help='强制使用的源编码(如gb2312, gbk等)')
    parser.add_argument('-o', '--output-encoding', default='utf-8', help='目标编码(默认utf-8)')
    parser.add_argument('-i', '--interactive', action='store_true', help='进入交互模式')
    
    args = parser.parse_args()
    
    if args.interactive or not any(vars(args).values()):
        # 交互模式或无参数时进入交互模式
        interactive_mode()
    else:
        # 命令行参数模式
        if not args.target:
            print("错误：必须指定目标路径")
            return
        
        if os.path.isdir(args.target) and not args.extension:
            print("错误：处理目录时必须指定文件扩展名")
            return
        
        if args.extension and not args.extension.startswith('.'):
            args.extension = '.' + args.extension
        
        print(f"开始转换目标 '{args.target}'...")
        process_target(args.target, args.extension, args.force_encoding, args.output_encoding)
        print("\n转换完成!")

if __name__ == "__main__":
    main()