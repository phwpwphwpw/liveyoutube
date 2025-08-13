import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import configparser
import os

class IniEditorApp:
    
    def __init__(self, root):
        self.root = root
        self.root.title("yt.ini 设置编辑器 (最终修正版)")
        self.root.geometry("820x580")

        # 主题中文翻译
        self.theme_translations = {
            'cerculean': '蔚蓝', 'cosmo': '宇宙', 'cyborg': '赛博格', 'darkly': '暗黑',
            'flatly': '扁平', 'journal': '日志', 'litera': '文学', 'lumen': '流明',
            'minty': '薄荷', 'morph': '变形', 'pulse': '脉冲', 'sandstone': '砂岩',
            'simplex': '简约', 'solar': '日光', 'superhero': '超级英雄', 'united': '联合',
            'vapor': '蒸汽', 'yeti': '雪人', 'zephyr': '和风'
        }

        # ConfigParser 初始化
        self.config = configparser.ConfigParser(
            comment_prefixes=('#'), 
            allow_no_value=True, 
            strict=False
        )
        self.config.optionxform = str # 保持键的大小写

        self.filepath = ""
        self.original_lines = [] # 用于存储原始文件的每一行
        self.widgets = {}

        # --- 界面布局 ---
        
        # 1. 顶部操作栏
        top_bar = ttk.Frame(root, padding=(10, 10, 10, 0))
        top_bar.pack(side=TOP, fill=X, anchor=N)

        # 1.1 文件操作区域
        file_ops_frame = ttk.Labelframe(top_bar, text=" 文件操作 ", padding=10)
        file_ops_frame.pack(side=LEFT, fill=Y, padx=(0, 10))
        
        ttk.Button(file_ops_frame, text="载入 yt.ini", command=self.load_ini, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 5))
        ttk.Button(file_ops_frame, text="保存 (保留格式)", command=self.save_ini, bootstyle=PRIMARY).pack(side=LEFT, padx=(0, 5))
        ttk.Button(file_ops_frame, text="另存为...", command=self.save_ini_as, bootstyle=INFO).pack(side=LEFT)
        
        # 1.2 主题选择区域
        theme_frame = ttk.Labelframe(top_bar, text=" 界面主题 ", padding=10)
        theme_frame.pack(side=LEFT, fill=Y)
        
        self.theme_menu_button = ttk.Menubutton(theme_frame, text="选择主题", bootstyle="secondary")
        self.theme_menu_button.pack(side=LEFT)
        
        menu = tk.Menu(self.theme_menu_button, tearoff=0)
        self.theme_var = tk.StringVar(value=self.root.style.theme.name)
        
        for theme_name in sorted(self.root.style.theme_names()):
            chinese_name = self.theme_translations.get(theme_name, theme_name.capitalize())
            menu.add_radiobutton(
                label=chinese_name, 
                variable=self.theme_var, 
                value=theme_name,
                command=self.change_theme
            )
        self.theme_menu_button["menu"] = menu

        # 2. 主体 Notebook (页签)
        main_frame = ttk.Frame(root, padding=(10, 10, 10, 10))
        main_frame.pack(expand=True, fill=BOTH)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill=BOTH)

        # 创建所有页签
        self.create_douyin_tab()
        self.create_youtube_tab()
        self.create_ffmpeg_tab()
        self.create_system_tab()
        
        # 载入预设的 yt.ini 内容
        self.load_default_config()

    def change_theme(self):
        selected_theme = self.theme_var.get()
        self.root.style.theme_use(selected_theme)

    def create_widget_row(self, parent, label_text, key, section, row, widget_type="entry", options=None, has_browse=False, browse_type="file"):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=W, padx=5, pady=8)
        container = ttk.Frame(parent)
        container.grid(row=row, column=1, sticky=EW, padx=5)
        
        widget = None
        if widget_type == "entry":
            widget = ttk.Entry(container, width=60)
            widget.pack(side=LEFT, expand=True, fill=X)
        elif widget_type == "combo":
            widget = ttk.Combobox(container, values=options, width=57, state="readonly")
            widget.pack(side=LEFT, expand=True, fill=X)
        elif widget_type == "text":
            text_container = ttk.Frame(container, bootstyle=SECONDARY, padding=1)
            text_container.pack(expand=True, fill=BOTH)
            widget = tk.Text(text_container, height=4, width=58, wrap=WORD, relief=FLAT)
            widget.pack(expand=True, fill=BOTH)
            
        if has_browse:
            browse_cmd = lambda w=widget: self.browse_file(w, browse_type)
            ttk.Button(container, text="浏览...", command=browse_cmd, bootstyle=OUTLINE).pack(side=LEFT, padx=(5,0))

        if section not in self.widgets: self.widgets[section] = {}
        self.widgets[section][key] = widget
        parent.columnconfigure(1, weight=1)

    # --- 抖音 (Douyin) 页签 ---
    def create_douyin_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="抖音 (Douyin)")

        id_frame = ttk.Labelframe(tab, text=" 主播ID列表 (douyin_ids) ", padding=10)
        id_frame.pack(fill=X, pady=5, ipady=5)
        
        list_frame = ttk.Frame(id_frame)
        list_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        list_container = ttk.Frame(list_frame, bootstyle=SECONDARY, padding=1)
        list_container.pack(fill=BOTH, expand=True)
        id_listbox = tk.Listbox(list_container, height=8, relief=FLAT, borderwidth=0)
        id_scrollbar = ttk.Scrollbar(list_container, orient=VERTICAL, command=id_listbox.yview, bootstyle=ROUND)
        id_listbox.configure(yscrollcommand=id_scrollbar.set)
        id_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        id_scrollbar.pack(side=RIGHT, fill=Y)
        if "Douyin" not in self.widgets: self.widgets["Douyin"] = {}
        self.widgets["Douyin"]["douyin_ids"] = id_listbox
        
        action_frame = ttk.Frame(id_frame)
        action_frame.pack(side=RIGHT, fill=Y)
        ttk.Label(action_frame, text="输入ID:").pack(anchor=W)
        new_id_entry = ttk.Entry(action_frame)
        new_id_entry.pack(fill=X, pady=(2, 10))
        ttk.Button(action_frame, text="新增ID", command=lambda: self.add_douyin_id(new_id_entry, id_listbox)).pack(fill=X)
        ttk.Button(action_frame, text="编辑选定ID", command=lambda: self.edit_douyin_id(id_listbox), bootstyle=(SECONDARY, OUTLINE)).pack(fill=X, pady=5)
        ttk.Button(action_frame, text="删除选定ID", command=lambda: self.delete_douyin_id(id_listbox), bootstyle=(DANGER, OUTLINE)).pack(fill=X)

        other_settings_frame = ttk.Labelframe(tab, text=" 其他设置 ", padding=10)
        other_settings_frame.pack(fill=X, pady=(10,0))
        self.create_widget_row(other_settings_frame, "备用视频路径:", "standby_video_path", "Douyin", 1, has_browse=True, browse_type="video")
        self.create_widget_row(other_settings_frame, "等待时间 (秒):", "wait_time", "Douyin", 2)
        self.create_widget_row(other_settings_frame, "检查间隔 (秒):", "check_interval", "Douyin", 3)

    # --- YouTube 页签 ---
    def create_youtube_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="YouTube")
        yt_frame = ttk.Labelframe(tab, text=" YouTube 直播设置 ", padding=10)
        yt_frame.pack(fill=BOTH, expand=True)

        self.create_widget_row(yt_frame, "凭证文件:", "client_secret_file", "YouTube", 0, has_browse=True, browse_type="json")
        self.create_widget_row(yt_frame, "直播标题:", "broadcast_title", "YouTube", 1)
        self.create_widget_row(yt_frame, "直播描述:", "broadcast_description", "YouTube", 2, widget_type="text")
        
        # 按照要求：只有分类ID是Textbox，其余是下拉
        self.create_widget_row(yt_frame, "分类ID:", "category_id", "YouTube", 3, widget_type="entry")
        self.create_widget_row(yt_frame, "隐私状态:", "privacy_status", "YouTube", 4, widget_type="combo", options=["public", "private", "unlisted"])
        self.create_widget_row(yt_frame, "自动开始:", "enable_auto_start", "YouTube", 5, widget_type="combo", options=["true", "false"])
        self.create_widget_row(yt_frame, "自动结束:", "enable_auto_stop", "YouTube", 6, widget_type="combo", options=["true", "false"])


    # --- FFmpeg 页签 ---
    def create_ffmpeg_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="FFmpeg")
        ffmpeg_frame = ttk.Labelframe(tab, text=" FFmpeg 转码设置 ", padding=10)
        ffmpeg_frame.pack(fill=BOTH, expand=True)

        self.create_widget_row(ffmpeg_frame, "FFmpeg路径:", "ffmpeg_path", "FFmpeg", 0, has_browse=True, browse_type="exe")
        self.create_widget_row(ffmpeg_frame, "视频比特率:", "bitrate", "FFmpeg", 1)
        self.create_widget_row(ffmpeg_frame, "编码器优先级:", "encoder_preference", "FFmpeg", 2)
        self.create_widget_row(ffmpeg_frame, "音频编码器:", "audio_codec", "FFmpeg", 3, widget_type="combo", options=["aac", "copy"])
        self.create_widget_row(ffmpeg_frame, "音频比特率:", "audio_bitrate", "FFmpeg", 4)
        self.create_widget_row(ffmpeg_frame, "NVENC预设:", "nvenc_preset", "FFmpeg", 5)
        self.create_widget_row(ffmpeg_frame, "QSV预设:", "qsv_preset", "FFmpeg", 6)
        self.create_widget_row(ffmpeg_frame, "CPU预设:", "cpu_preset", "FFmpeg", 7)
        self.create_widget_row(ffmpeg_frame, "CPU线程数:", "cpu_threads", "FFmpeg", 8)

    # --- 系统 (System) 页签 ---
    def create_system_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="系统 (System)")
        system_frame = ttk.Labelframe(tab, text=" 系统相关设置 ", padding=10)
        system_frame.pack(fill=BOTH, expand=True)
        
        self.create_widget_row(system_frame, "浏览器路径:", "browser_path", "System", 0, has_browse=True, browse_type="exe")
        self.create_widget_row(system_frame, "代理服务器 URL:", "proxy_url", "System", 1)

    # --- ID 列表管理函数 ---
    def add_douyin_id(self, entry, listbox):
        new_id = entry.get().strip()
        if new_id:
            if new_id not in listbox.get(0, tk.END):
                listbox.insert(tk.END, new_id)
                entry.delete(0, tk.END)
            else:
                messagebox.showwarning("提示", "这个ID已经存在于列表中。", parent=self.root)
        else:
            messagebox.showwarning("提示", "ID不能为空。", parent=self.root)

    def edit_douyin_id(self, listbox):
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请先在列表中选择一个要编辑的ID。", parent=self.root)
            return
        index = selected_indices[0]
        old_id = listbox.get(index)
        new_id = simpledialog.askstring("编辑ID", "请输入新的ID：", initialvalue=old_id, parent=self.root)
        if new_id and new_id.strip() != old_id:
            listbox.delete(index)
            listbox.insert(index, new_id.strip())

    def delete_douyin_id(self, listbox):
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请先在列表中选择一个或多个要删除的ID。", parent=self.root)
            return
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected_indices)} 个ID吗？", parent=self.root):
            for index in reversed(selected_indices):
                listbox.delete(index)

    # --- 核心功能函数 ---
    def browse_file(self, widget, file_type):
        filetypes_map = {
            "exe": [("可执行文件", "*.exe"), ("所有文件", "*.*")],
            "json": [("JSON 文件", "*.json"), ("所有文件", "*.*")],
            "video": [("视频文件", "*.mp4 *.flv *.ts"), ("所有文件", "*.*")]
        }
        filetypes = filetypes_map.get(file_type, [("所有文件", "*.*")])
        filename = filedialog.askopenfilename(title="选择文件", filetypes=filetypes, parent=self.root)
        if filename:
            if isinstance(widget, (ttk.Entry, tk.Entry)):
                widget.delete(0, tk.END)
                widget.insert(0, filename.replace("\\", "/"))

    def populate_form(self):
        for section, fields in self.widgets.items():
            if self.config.has_section(section):
                for key, widget in fields.items():
                    value = self.config.get(section, key, raw=True, fallback='').strip()
                    if key == 'douyin_ids' and isinstance(widget, tk.Listbox):
                        widget.delete(0, tk.END)
                        ids = [i.strip() for i in value.split(',') if i.strip()]
                        for an_id in ids: widget.insert(tk.END, an_id)
                    elif isinstance(widget, tk.Text):
                        widget.delete("1.0", tk.END)
                        widget.insert("1.0", value.strip('"'))
                    elif isinstance(widget, ttk.Combobox): # Combobox
                        widget.set(value)
                    elif isinstance(widget, ttk.Entry):
                         widget.delete(0, tk.END)
                         widget.insert(0, value)

    def load_default_config(self):
        # phwpw 
        default_ini_content = """[Douyin]
  # 要轮询的抖音主播ID列表，用英文逗号分隔。脚本会按顺序扫描。
  douyin_ids = 1121111,1121112
  # 本地备用视频文件的完整路径。当所有主播都未开播时，将循环推流此视频。
  # 请使用正斜杠 / 作为路径分隔符，例如 C:/videos/standby.mp4
  standby_video_path = C:/1.mp4
  # 使用浏览器打开抖音页面后，等待页面加载并抓取到直播地址的时间（秒）。
  wait_time = 15
  # 当主播未开播时，脚本会每隔这个设定的时间（秒）就去检查一次。
  check_interval = 60

[YouTube]
  # 授权后生成的凭证文件名，应与脚本放在同一目录或提供完整路径。
  client_secret_file = client_secret.json
  # YouTube直播的标题。
  broadcast_title = 24/7 Live Stream | Powered by test
  # YouTube直播的描述。
  broadcast_description = "This is a 24/7 live stream."
  # 分类ID，例如: 22=人物与博客, 26=方法与时尚, 24=娱乐, 20=游戏
  category_id = 24
  # 隐私状态: public, private, unlisted
  privacy_status = public
  # 是否允许YouTube在检测到推流信号后自动开始直播。
  enable_auto_start = true
  # 是否允许YouTube在推流信号中断后自动结束直播 (重要：在我们的方案中设为 false)。
  # 我们不希望YouTube自动结束，因为我们的脚本会快速恢复推流。
  enable_auto_stop = true

[FFmpeg]
  # ffmpeg.exe 程序的路径。如果已在环境变量中，写`ffmpeg`即可。
  ffmpeg_path = ffmpeg
  # 推送到YouTube的视频比特率。例如: 4000k
  bitrate = 4000k
  # 核心：编码器使用优先级，用逗号分隔。脚本会从左到右依次尝试。
  # 可用值: copy (直接复制), qsv (Intel核显), nvenc (NVIDIA显卡), cpu (CPU软件编码)
  encoder_preference = cpu
  # 音频编码器: copy = 直接复制, aac = 重新编码为AAC
  audio_codec = aac
  # 音频比特率 (仅在 audio_codec 不是 copy 时有效)。例如 128k
  audio_bitrate = 128k
  # --- 各种编码器的预设参数 ---
  nvenc_preset = p5
  qsv_preset = fast
  cpu_preset = veryfast
  cpu_threads = 4

[System]
  # Playwright使用的浏览器路径 (可选，留空则使用默认安装的)。
  browser_path = C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe
  # 系统代理设置。留空则不使用代理。格式: http://127.0.0.1:7890
  proxy_url = http://127.0.0.1:7890
"""
        self.config.read_string(default_ini_content)
        self.original_lines = default_ini_content.strip().splitlines(keepends=True)
        self.populate_form()

    def load_ini(self):
        filepath = filedialog.askopenfilename(title="选择 yt.ini 文件", filetypes=[("INI 文件", "*.ini"), ("所有文件", "*.*")], parent=self.root)
        if filepath:
            self.filepath = filepath
            try:
                self.config = configparser.ConfigParser(comment_prefixes=('#'), allow_no_value=True, strict=False)
                self.config.optionxform = str
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.config.read_file(f)
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.original_lines = f.readlines()
                
                self.populate_form()
                self.root.title(f"yt.ini 专业设置管理器 - {os.path.basename(filepath)}")
                messagebox.showinfo("成功", f"已成功载入 {os.path.basename(filepath)}", parent=self.root)
            except Exception as e:
                messagebox.showerror("错误", f"载入文件时发生错误:\n{e}", parent=self.root)

    def save_ini_as(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".ini", filetypes=[("INI 文件", "*.ini"), ("所有文件", "*.*")], title="另存为...", parent=self.root)
        if filepath:
            save_config = configparser.ConfigParser(comment_prefixes=('#'), allow_no_value=True)
            save_config.optionxform = str
            updated_values = self.get_updated_values_from_form()
            for section, values in updated_values.items():
                save_config[section] = {}
                for key, value in values.items():
                    save_config[section][key] = value

            with open(filepath, 'w', encoding='utf-8') as configfile:
                save_config.write(configfile)
            messagebox.showinfo("成功", f"设置已作为新文件保存至\n{filepath}", parent=self.root)

    def save_ini(self):
        """
        核心功能：保存设置到原始文件，并完整保留注解、格式和空白行。
        """
        if not self.filepath or not self.original_lines:
            messagebox.showwarning("警告", "请先载入一个 `yt.ini` 文件才能使用“保存(保留格式)”功能。\n您也可以使用“另存为”来创建新文件。", parent=self.root)
            return

        updated_values = self.get_updated_values_from_form()
        new_lines = []
        current_section = ""

        for line in self.original_lines:
            stripped_line = line.strip()

            if stripped_line.startswith('[') and stripped_line.endswith(']'):
                current_section = stripped_line[1:-1]
                new_lines.append(line)
                continue
            
            if stripped_line.startswith('#') or not stripped_line:
                new_lines.append(line)
                continue

            if '=' in line:
                key = line.split('=', 1)[0].strip()
                if current_section in updated_values and key in updated_values[current_section]:
                    new_value = updated_values[current_section].get(key)
                    indentation = line[:len(line) - len(line.lstrip())]
                    new_lines.append(f"{indentation}{key} = {new_value}\n")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            messagebox.showinfo("成功", f"设置已成功保存至\n{self.filepath}\n注解和格式已保留。", parent=self.root)
        except Exception as e:
            messagebox.showerror("错误", f"保存文件时发生错误:\n{e}", parent=self.root)
            
    def get_updated_values_from_form(self):
        updated_values = {}
        for section, fields in self.widgets.items():
            updated_values[section] = {}
            for key, widget in fields.items():
                value = ''
                if key == 'douyin_ids' and isinstance(widget, tk.Listbox):
                    value = ",".join(widget.get(0, tk.END))
                elif isinstance(widget, tk.Text):
                    value = widget.get("1.0", tk.END).strip()
                else:
                    value = widget.get().strip()
                updated_values[section][key] = value
        return updated_values

if __name__ == "__main__":
    # 预设主题为 "cyborg"
    root = ttk.Window(themename="cyborg")
    app = IniEditorApp(root)
    root.mainloop()
