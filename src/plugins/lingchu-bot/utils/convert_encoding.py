import os
import argparse
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, simpledialog

# 定义常见编码列表
ENCODINGS = [
    "utf-8",
    "gb2312",
    "gbk",
    "big5",
    "utf-16",
    "utf-16le",
    "utf-16be",
    "ascii",
]


def detect_encoding(file_path: str) -> str | None:
    """
    尝试用常见编码检测文件编码。

    :param file_path: 要检测编码的文件路径
    :return: 检测到的编码，若未检测到则返回 None
    """
    for encoding in ENCODINGS:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue
    return None


def convert_file(
    file_path: str, target_encoding: str = "utf-8", source_encoding: str | None = None
) -> tuple[bool, str]:
    """
    将单个文件转换为指定编码。

    :param file_path: 要转换的文件路径
    :param target_encoding: 目标编码，默认为 utf-8
    :param source_encoding: 源文件编码，若未指定则自动检测
    :return: 转换结果元组 (是否成功, 消息)
    """
    encoding = source_encoding or detect_encoding(file_path)
    if not encoding:
        return False, "无法检测到文件编码"

    try:
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()
        with open(file_path, "w", encoding=target_encoding) as f:
            f.write(content)
        return True, "文件转换成功"
    except Exception as e:
        return False, f"文件转换失败: {str(e)}"


def process_files(
    target: str,
    target_encoding: str = "utf-8",
    source_encoding: str | None = None,
    extension: str | None = None,
) -> list[tuple[bool, str]]:
    """
    处理文件或目录，进行编码转换。

    :param target: 文件或目录路径
    :param target_encoding: 目标编码，默认为 utf-8
    :param source_encoding: 源文件编码，若未指定则自动检测
    :param extension: 处理目录时需要指定的文件扩展名
    :return: 每个文件转换结果的列表
    """
    if os.path.isfile(target):
        if not extension or target.lower().endswith(extension.lower()):
            return [convert_file(target, target_encoding, source_encoding)]
    elif os.path.isdir(target):
        if not extension:
            raise ValueError("处理目录时必须指定文件扩展名")
        results = []
        for root, _, files in os.walk(target):
            for file in files:
                if file.lower().endswith(extension.lower()):
                    file_path = os.path.join(root, file)
                    results.append(
                        convert_file(file_path, target_encoding, source_encoding)
                    )
        return results
    return []


class EncodingConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("文件编码转换工具")
        self._setup_ui()
        self._setup_style()
        self._setup_window()
        self._start_fade_in()

    def _setup_ui(self):
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)
        self.root.configure(bg="#2d2d2d")

        self.title_bar = tk.Frame(
            self.root, bg="#252525", relief="raised", bd=0, height=30
        )
        self.title_bar.pack(fill=tk.X)

        title_label = tk.Label(
            self.title_bar,
            text="文件编码转换工具",
            bg="#252525",
            fg="white",
            font=("微软雅黑", 10, "bold"),
        )
        title_label.pack(side=tk.LEFT, padx=10)

        close_button = tk.Button(
            self.title_bar,
            text="×",
            command=self.root.destroy,
            bg="#252525",
            fg="white",
            bd=0,
            activebackground="red",
            activeforeground="white",
            font=("Arial", 12, "bold"),
            padx=10,
        )

        def on_press():
            close_button.config(bg="darkred", fg="white")

        def on_release():
            close_button.config(bg="#252525", fg="white")

        close_button.bind("<ButtonPress-1>", lambda e: on_press())
        close_button.bind("<ButtonRelease-1>", lambda e: on_release())
        close_button.pack(side=tk.RIGHT)

        self.x = None
        self.y = None
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<ButtonRelease-1>", self.stop_move)
        self.title_bar.bind("<B1-Motion>", self.on_move)

        main_frame = tk.Frame(self.root, bg="#2d2d2d", padx=20, pady=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        header_frame = tk.Frame(main_frame, bg="#2d2d2d")
        header_frame.pack(pady=(0, 20))

        title_text = tk.Label(
            header_frame,
            text="文件编码转换工具",
            bg="#2d2d2d",
            fg="white",
            font=("微软雅黑", 14, "bold"),
        )
        title_text.pack()

        btn_frame = tk.Frame(main_frame, bg="#2d2d2d")
        btn_frame.pack(expand=True)

        ttk.Separator(main_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        btn_style = {"style": "Custom.TButton", "width": 20}

        file_btn = ttk.Button(
            btn_frame, text="📁 选择文件", command=self.browse_file, **btn_style
        )
        file_btn.pack(pady=10)

        dir_btn = ttk.Button(
            btn_frame, text="📂 选择目录", command=self.browse_directory, **btn_style
        )
        dir_btn.pack(pady=10)

        self.progress_bar = ttk.Progressbar(main_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=10)
        self.progress_bar.pack_forget()

        footer = tk.Label(
            main_frame,
            text="灵初机器人 - 文件编码转换工具",
            bg="#2d2d2d",
            fg="#666666",
            font=("微软雅黑", 8),
        )
        footer.pack(side=tk.BOTTOM, pady=10)

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            ".", background="#2d2d2d", foreground="white", font=("微软雅黑", 10)
        )

        style.configure(
            "Custom.TButton",
            background="#3d3d3d",
            foreground="white",
            padding=10,
            borderwidth=0,
            relief="flat",
            font=("微软雅黑", 12),
        )
        style.map(
            "Custom.TButton",
            background=[
                ("active", "#4d4d4d"),
                ("pressed", "#5d5d5d"),
                ("hover", "#4d4d4d"),
            ],
            relief=[("pressed", "sunken")],
        )

        style.configure(
            "TLabel", background="#2d2d2d", foreground="white", font=("微软雅黑", 10)
        )
        style.configure("TFrame", background="#2d2d2d")

    def _setup_window(self):
        window_width = 450
        window_height = 350
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _start_fade_in(self):
        alpha = self.root.attributes("-alpha")
        if alpha < 1.0:
            alpha += 0.05
            self.root.attributes("-alpha", alpha)
            self.root.after(20, self._start_fade_in)

    def start_move(self, event: tk.Event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event: tk.Event):
        self.x = None
        self.y = None

    def on_move(self, event: tk.Event):
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            new_x = self.root.winfo_x() + deltax
            new_y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{new_x}+{new_y}")

    def browse_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.progress_bar.pack()
            self.progress_bar["value"] = 0
            self.root.update()
            success, message = convert_file(file_path)
            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("错误", message)
            self.progress_bar["value"] = 100
            self.root.update()
            self.progress_bar.pack_forget()

    def browse_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            extension = simpledialog.askstring(
                "输入扩展名", "请输入要处理的文件扩展名(如.txt):"
            )
            if extension:
                try:
                    self.progress_bar.pack()
                    self.progress_bar["value"] = 0
                    self.root.update()
                    results = process_files(dir_path, extension=extension)
                    success_count = sum(1 for success, _ in results if success)
                    total_count = len(results)
                    messagebox.showinfo(
                        "成功",
                        f"目录 {os.path.basename(dir_path)} 下 {success_count}/{total_count} 个.{extension} 文件转换完成",
                    )
                except Exception as e:
                    messagebox.showerror("错误", str(e))
                finally:
                    self.progress_bar["value"] = 100
                    self.root.update()
                    self.progress_bar.pack_forget()


def create_gui():
    root = tk.Tk()
    app = EncodingConverterApp(root)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="文件编码转换工具")
    parser.add_argument("target", nargs="?", help="文件或目录路径")
    parser.add_argument("-e", "--extension", help="文件扩展名(处理目录时需要)")
    parser.add_argument("-f", "--force-encoding", help="强制使用的源编码")
    parser.add_argument(
        "-o", "--output-encoding", default="utf-8", help="目标编码(默认utf-8)"
    )
    parser.add_argument("-g", "--gui", action="store_true", help="启动交互式GUI模式")

    args = parser.parse_args()

    if args.gui or not args.target:
        create_gui()
    else:
        try:
            results = process_files(
                args.target, args.output_encoding, args.force_encoding, args.extension
            )
            success_count = sum(1 for success, _ in results if success)
            total_count = len(results)
            print(f"转换完成，成功: {success_count}/{total_count}")
        except Exception as e:
            print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()
