import os
import sys
import subprocess
import re
import configparser
import threading
from queue import Queue, Empty
import time
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText

class DependencyInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python 依賴庫管理器 (我从山上来)")
        self.root.geometry("950x750")

        self.interpreters = {}
        self.output_queue = Queue()
        
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        top_controls_frame = ttk.Frame(main_frame)
        top_controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        setup_frame = ttk.Labelframe(top_controls_frame, text=" 步驟一：環境設定 ", padding=10)
        setup_frame.pack(side=LEFT, fill=Y, padx=(0, 10))
        
        ttk.Button(setup_frame, text="掃描 Python 環境", command=self.start_scan, bootstyle=PRIMARY).grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.ini_path_var = tk.StringVar(value=self.get_default_ini_path())
        self.ini_entry = ttk.Entry(setup_frame, textvariable=self.ini_path_var, width=40)
        self.ini_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(setup_frame, text="選擇 INI", command=self.select_ini_file, bootstyle=SECONDARY).grid(row=1, column=1, padx=5, pady=5)

        action_frame = ttk.Labelframe(top_controls_frame, text=" 步驟二：執行操作 ", padding=10)
        action_frame.pack(side=LEFT, fill=Y)

        ttk.Button(action_frame, text="全部檢查", command=self.start_check_all_packages, bootstyle=INFO).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ttk.Button(action_frame, text="安裝缺少項", command=self.start_install_missing, bootstyle=DANGER).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        self.single_package_var = tk.StringVar()
        self.single_package_entry = ttk.Entry(action_frame, textvariable=self.single_package_var, width=20)
        self.single_package_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(action_frame, text="安裝此庫", command=self.start_install_single_package, bootstyle=SUCCESS).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        # --- 新增卸載按鈕 ---
        ttk.Button(action_frame, text="卸載此庫", command=self.start_uninstall_single_package, bootstyle=(OUTLINE, DANGER)).grid(row=1, column=2, sticky="ew", padx=5, pady=5)

        tree_frame = ttk.Labelframe(main_frame, text=" 步驟三：檢查與安裝狀態 ", padding=10)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        
        columns = ("path", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", bootstyle=INFO)
        
        self.tree.heading("#0", text="Python 版本")
        self.tree.heading("path", text="依賴庫 / 路徑")
        self.tree.heading("status", text="狀態")

        self.tree.column("path", width=450)
        self.tree.column("status", width=150, anchor='center')
        self.tree.column("#0", width=200, stretch=False)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)
        self.checked_items = set()

        log_frame = ttk.Labelframe(main_frame, text=" 執行日誌 ", padding=10)
        log_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        self.log_text = ScrolledText(log_frame, height=10, wrap=tk.WORD, autohide=True, bootstyle=DARK)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.text.config(state=tk.DISABLED)

        self.root.after(100, self.process_queue)

    def get_default_ini_path(self):
        try:
            base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, 'dependencies.ini')

    def select_ini_file(self):
        filepath = filedialog.askopenfilename(
            title="選擇依賴庫設定檔",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.get_default_ini_path())
        )
        if filepath:
            self.ini_path_var.set(filepath)

    def log(self, message):
        self.log_text.text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.text.config(state=tk.DISABLED)

    def process_queue(self):
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.log(message)
        except Empty:
            pass
        self.root.after(100, self.process_queue)

    def start_thread(self, target_func, *args):
        thread = threading.Thread(target=target_func, args=args, daemon=True)
        thread.start()

    def start_scan(self):
        self.start_thread(self.find_python_interpreters)

    def start_check_all_packages(self):
        all_ids = list(self.interpreters.keys())
        if not all_ids:
            self.log("⚠️ 請先掃描Python環境。")
            return
        self.log("ℹ️ 將為所有掃描到的環境檢查依賴...")
        for item_id in all_ids:
            if item_id not in self.checked_items:
                self.checked_items.add(item_id)
                self.tree.item(item_id, image='checked')
        self.start_thread(self.check_packages, all_ids)
        
    def start_install_missing(self):
        selected_ids = list(self.checked_items)
        if not selected_ids:
            self.log("⚠️ 請先勾選環境或執行「全部檢查」。")
            return
        self.start_thread(self.install_all_missing, selected_ids)
        
    def start_install_single_package(self):
        package_name = self.single_package_var.get().strip()
        if not package_name:
            self.log("⚠️ 請在輸入框中指定要安裝的庫名。")
            return
        
        selected_ids = list(self.checked_items)
        if not selected_ids:
            self.log(f"⚠️ 請先勾選要為哪個Python環境安裝 '{package_name}'。")
            return
            
        self.start_thread(self.install_single_package, package_name, selected_ids)

    # --- 新增的卸載啟動函式 ---
    def start_uninstall_single_package(self):
        package_name = self.single_package_var.get().strip()
        if not package_name:
            self.log("⚠️ 請在輸入框中指定要卸載的庫名。")
            return
        
        selected_ids = list(self.checked_items)
        if not selected_ids:
            self.log(f"⚠️ 請先勾選要從哪個Python環境卸載 '{package_name}'。")
            return
            
        self.start_thread(self.uninstall_single_package, package_name, selected_ids)

    def on_tree_click(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        if "image" in elem:
            item_id = self.tree.identify_row(y)
            if item_id in self.checked_items:
                self.checked_items.remove(item_id)
                self.tree.item(item_id, image='')
            else:
                self.checked_items.add(item_id)
                self.tree.item(item_id, image='checked')

    def _create_checkbox_images(self):
        img_checked = tk.PhotoImage(name='checked', data='R0lGODlhCwALAJEAAAAAAP///83PDwAAAAAAACH5BAEAAAIALAAAAAALAAsAAAIRnC2nrsPj2AlzbcMWXpw25ocmADs=')
        img_unchecked = tk.PhotoImage(name='unchecked', data='R0lGODlhCwALAJEAAAAAAO7u7gAAAAAAACH5BAEAAAIALAAAAAALAAsAAAIMlI+py+0Bopx22y2BIAQAOw==')
        self.root.imglist = (img_checked, img_unchecked)

    def find_python_interpreters(self):
        self.log("🔍 正在掃描系統中的 Python 版本...")
        self.root.after(0, lambda: self.tree.delete(*self.tree.get_children()))
        self.interpreters.clear()
        self.checked_items.clear()
        paths = os.environ.get("PATH", "").split(os.pathsep)
        found_paths = set()
        if sys.platform == "win32":
            try:
                result = subprocess.run(['py', '-0p'], capture_output=True, text=True, check=True, encoding='utf-8')
                for line in result.stdout.strip().splitlines():
                    if line.startswith('-') and '\t' in line:
                        path = line.split('\t')[-1].strip()
                        if path.endswith("python.exe") and os.path.exists(path):
                            found_paths.add(os.path.normpath(path))
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.log("  - 未找到 'py' 啟動器，將掃描 PATH 環境變數...")
        for path_dir in paths:
            if not os.path.isdir(path_dir): continue
            for file in os.listdir(path_dir):
                if (sys.platform == "win32" and (file.lower() == "python.exe" or re.match(r'^python3(\.\d+)?\.exe$', file.lower()))) or \
                   (sys.platform != "win32" and re.match(r'^python3(\.\d+)?$', file)):
                    found_paths.add(os.path.normpath(os.path.join(path_dir, file)))
        interpreter_list = []
        for path in sorted(list(found_paths)):
            try:
                version_result = subprocess.run([path, "--version"], capture_output=True, text=True, check=True, encoding='utf-8')
                version = version_result.stdout.strip()
                interpreter_list.append({'name': version, 'path': path})
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        def populate_tree():
            self._create_checkbox_images()
            for interp in interpreter_list:
                item_id = self.tree.insert("", tk.END, text=interp['name'], values=(interp['path'], "待檢查"), image='unchecked')
                self.interpreters[item_id] = {'path': interp['path'], 'name': interp['name'], 'missing': []}
            
            if not self.interpreters:
                self.log("❌ 錯誤：在您的系統中找不到任何 Python 解釋器。")
            else:
                self.log(f"✅ 成功找到 {len(self.interpreters)} 個 Python 版本！")
        self.root.after(0, populate_tree)

    def get_required_packages(self):
        config = configparser.ConfigParser()
        ini_path = self.ini_path_var.get()
        if not os.path.exists(ini_path):
            self.log(f"❌ 錯誤: 找不到依賴庫設定檔 '{ini_path}'")
            try:
                with open(ini_path, 'w', encoding='utf-8') as f:
                    f.write("[Dependencies]\n# 格式為：pip安裝時的名稱 = import時檢查的名稱\n")
                    f.write("ttkbootstrap = ttkbootstrap\nPillow = PIL\n")
                self.log(f"📝 已在程式目錄創建預設的 'dependencies.ini' 文件，請依需求修改。")
            except Exception as e:
                self.log(f"❌ 創建預設設定檔失敗: {e}")
            return None
        config.read(ini_path, encoding='utf-8')
        if 'Dependencies' not in config:
            self.log(f"❌ 錯誤: 設定檔中缺少 [Dependencies] 部分。")
            return None
        return config['Dependencies']

    def _update_package_status_in_tree(self, parent_id, pip_name, is_installed):
        if is_installed:
            self.tree.insert(parent_id, tk.END, text="", values=(pip_name, "已安裝"), tags=('installed',))
        else:
            self.tree.insert(parent_id, tk.END, text="", values=(pip_name, "缺少"), tags=('missing',))

    def _update_parent_status_in_tree(self, item_id, python_exe, interpreter_name, missing_list):
        if not missing_list:
            self.tree.item(item_id, values=(python_exe, "依賴完整"))
            self.log(f"✅ {interpreter_name} 的依賴庫完整！")
        else:
            self.tree.item(item_id, values=(python_exe, f"缺少 {len(missing_list)} 項"))
            self.log(f"🟡 {interpreter_name} 缺少 {len(missing_list)} 個依賴。")
    
    def _configure_tree_tags(self):
        self.tree.tag_configure('installed', foreground='lightgreen')
        self.tree.tag_configure('missing', foreground='lightcoral')

    def check_packages(self, selected_ids):
        required_packages = self.get_required_packages()
        if not required_packages: return
        
        self.root.after(0, self._configure_tree_tags)
        for item_id in selected_ids:
            self.root.after(0, lambda id=item_id: [self.tree.delete(child) for child in self.tree.get_children(id)])
            interpreter_info = self.interpreters[item_id]
            python_exe = interpreter_info['path']
            self.log(f"\n--- 正在檢查 {interpreter_info['name']} 的依賴庫 ---")
            current_missing_list = []
            for pip_name, import_name in required_packages.items():
                try:
                    subprocess.run([python_exe, "-c", f"import {import_name}"], check=True, capture_output=True, text=True)
                    self.root.after(0, self._update_package_status_in_tree, item_id, pip_name, True)
                except subprocess.CalledProcessError:
                    current_missing_list.append(pip_name)
                    self.root.after(0, self._update_package_status_in_tree, item_id, pip_name, False)
            
            interpreter_info['missing'] = current_missing_list
            self.root.after(100, self._update_parent_status_in_tree, item_id, python_exe, interpreter_info['name'], current_missing_list)

    def install_all_missing(self, selected_ids):
        for item_id in selected_ids:
            info = self.interpreters.get(item_id)
            if not info or 'missing' not in info or not info['missing']:
                self.log(f"⏭️ 跳過 {info.get('name', '未知環境')}，因其依賴完整或未檢查。")
                continue
            python_exe = info['path']
            missing_packages_copy = list(info['missing'])
            self.log(f"\n--- 正在為 {info['name']} 安裝依賴 ---")
            for pkg in missing_packages_copy:
                if pkg not in info['missing']: continue
                self.log(f"\n⏳ 正在安裝 {pkg}...")
                command = [python_exe, "-m", "pip", "install", "--upgrade", "--user", pkg]
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
                for line in iter(process.stdout.readline, ''):
                    self.output_queue.put(line.strip())
                process.wait()
                if process.returncode == 0:
                    self.log(f"✅ {pkg} 安裝成功！")
                    if pkg in info['missing']: info['missing'].remove(pkg)
                    if pkg == "playwright":
                        self.log("  -> 偵測到 playwright，正在安裝瀏覽器核心...")
                        pw_command = [python_exe, "-m", "playwright", "install"]
                        pw_process = subprocess.Popen(pw_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
                        for line in iter(pw_process.stdout.readline, ''):
                            self.output_queue.put(line.strip())
                        self.log("  -> 瀏覽器核心安裝完畢！")
                else:
                    self.log(f"❌ {pkg} 安裝失敗，返回碼: {process.returncode}")
            
            self.root.after(0, self._update_parent_status_in_tree, item_id, python_exe, info['name'], info['missing'])
            
    def install_single_package(self, package_name, selected_ids):
        any_success = False
        for item_id in selected_ids:
            info = self.interpreters.get(item_id)
            if not info: continue
            
            python_exe = info['path']
            self.log(f"\n--- 正在為 {info['name']} 安裝 '{package_name}' ---")
            command = [python_exe, "-m", "pip", "install", "--upgrade", "--user", package_name]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            
            for line in iter(process.stdout.readline, ''):
                self.output_queue.put(line.strip())
            process.wait()
            if process.returncode == 0:
                self.log(f"✅ 在 {info['name']} 中成功安裝 '{package_name}'！")
                any_success = True
            else:
                self.log(f"❌ 在 {info['name']} 中安裝 '{package_name}' 失敗，返回碼: {process.returncode}")

        if any_success:
            self.add_package_to_ini(package_name)

    # --- 新增的卸載函式 ---
    def uninstall_single_package(self, package_name, selected_ids):
        """為選中的Python環境卸載單個庫"""
        any_success = False
        for item_id in selected_ids:
            info = self.interpreters.get(item_id)
            if not info: continue
            
            python_exe = info['path']
            self.log(f"\n--- 正在為 {info['name']} 卸載 '{package_name}' ---")
            # 使用 -y 參數來自動確認卸載，避免程式掛起
            command = [python_exe, "-m", "pip", "uninstall", "-y", package_name]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            
            for line in iter(process.stdout.readline, ''):
                self.output_queue.put(line.strip())
            process.wait()

            if process.returncode == 0:
                self.log(f"✅ 在 {info['name']} 中成功卸載 '{package_name}'！")
                any_success = True
            else:
                self.log(f"❌ 在 {info['name']} 中卸載 '{package_name}' 失敗，返回碼: {process.returncode}")

        if any_success:
            self.remove_package_from_ini(package_name)

    def add_package_to_ini(self, package_name):
        self.log(f"\nℹ️ 正在嘗試將 '{package_name}' 添加到設定檔...")
        ini_path = self.ini_path_var.get()
        config = configparser.ConfigParser()
        try:
            config.read(ini_path, encoding='utf-8')
            if 'Dependencies' not in config:
                config['Dependencies'] = {}

            if package_name in config['Dependencies']:
                self.log(f"👍 '{package_name}' 已存在於設定檔中，無需添加。")
                return

            import_name = package_name.lower().replace('-', '_')
            config.set('Dependencies', package_name, import_name)
            
            with open(ini_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            
            self.log(f"✅ 成功將 '{package_name} = {import_name}' 添加到 {os.path.basename(ini_path)}。")
            self.log(f"   請注意：導入名被假定為 '{import_name}'，如有特殊情況請手動修改。")
        except Exception as e:
            self.log(f"❌ 自動更新設定檔失敗: {e}")

    # --- 新增的從INI移除函式 ---
    def remove_package_from_ini(self, package_name):
        """從INI設定檔中移除成功卸載的庫"""
        self.log(f"\nℹ️ 正在嘗試從設定檔中移除 '{package_name}'...")
        ini_path = self.ini_path_var.get()
        config = configparser.ConfigParser()
        try:
            config.read(ini_path, encoding='utf-8')
            if 'Dependencies' not in config or package_name not in config['Dependencies']:
                self.log(f"👍 '{package_name}' 本來就不在設定檔中，無需移除。")
                return

            config.remove_option('Dependencies', package_name)
            
            with open(ini_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            
            self.log(f"✅ 成功從 {os.path.basename(ini_path)} 中移除了 '{package_name}'。")

        except Exception as e:
            self.log(f"❌ 自動更新設定檔失敗: {e}")


if __name__ == "__main__":
    root = ttk.Window(themename="cyborg")
    app = DependencyInstallerApp(root)
    root.mainloop()
