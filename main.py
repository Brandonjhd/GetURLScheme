import customtkinter as ctk
import os
import zipfile
import plistlib
import threading
from tkinter import filedialog, messagebox
import json

# 设置UI外观和主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
info_size = 13
info_height = 10


class IPAURLSchemeExtractor:
    # 初始化
    def __init__(self):
        pass

    # 从 IPA 文件中提取 Info.plist
    def extract_info_plist(self, ipa_path, callback=None):
        if callback:
            callback(f"正在解析 {os.path.basename(ipa_path)}...\n")
        try:
            with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
                for filename in zip_ref.namelist():
                    # 只处理标准Payload目录下的Info.plist
                    if 'Payload/' in filename and filename.endswith('.app/Info.plist'):
                        with zip_ref.open(filename) as plist_file:
                            return plistlib.load(plist_file)
            if callback:
                callback("未找到Info.plist文件\n")
            return None
        except Exception as e:
            if callback:
                callback(f"提取失败: {e}\n")
            return None

    # 提取 URL Schemes
    def extract_url_schemes(self, plist_data):
        url_schemes = []
        if not plist_data:
            return url_schemes
        bundle_url_types = plist_data.get('CFBundleURLTypes', [])
        for url_type in bundle_url_types:
            schemes = url_type.get('CFBundleURLSchemes', [])
            url_schemes.extend(schemes)
        return url_schemes

    # 提取应用基本信息
    def extract_app_info(self, plist_data):
        if not plist_data:
            return {}
        return {
            'app_name': plist_data.get('CFBundleName', 'Unknown'),
            'bundle_id': plist_data.get('CFBundleIdentifier', 'Unknown'),
            'version': plist_data.get('CFBundleShortVersionString', 'Unknown'),
            'build': plist_data.get('CFBundleVersion', 'Unknown')
        }


class ModernIPAToolApp(ctk.CTk):
    # 初始化主窗口
    def __init__(self):
        super().__init__()
        self.title("iOS URL Scheme 提取器")
        self.geometry("900x700")
        self.minsize(800, 600)
        self.extractor = IPAURLSchemeExtractor()
        self.current_schemes = []
        self.current_app_info = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.create_main_content()

    # 快速创建 CTkLabel
    @staticmethod
    def make_label(parent, text, size=14, bold=False, color=None, anchor="w", height=info_height):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
            text_color=color,
            anchor=anchor,
            height=height
        )

    # UI布局创建
    def create_main_content(self):
        # 主容器
        main_container = ctk.CTkFrame(self, corner_radius=15)
        main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(5, weight=1)

        # 标题栏
        title_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))
        self.make_label(title_frame, "📱 iOS URL Scheme 提取器", size=28, bold=True).pack(side="left")
        appearance_menu = ctk.CTkOptionMenu(
            title_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode,
            width=120
        )
        appearance_menu.set("System")
        appearance_menu.pack(side="right", padx=10)

        # 文件选择区域
        file_frame = ctk.CTkFrame(main_container)
        file_frame.grid(row=1, column=0, padx=30, pady=15, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)
        self.make_label(file_frame, "IPA 文件:", size=15, bold=True).grid(row=0, column=0, padx=15, pady=15)
        self.file_path_entry = ctk.CTkEntry(
            file_frame,
            placeholder_text="点击浏览按钮选择 IPA 文件...",
            height=45,
            font=ctk.CTkFont(size=14),
            state="readonly"
        )
        self.file_path_entry.grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        browse_btn = ctk.CTkButton(
            file_frame,
            text="📁 浏览",
            command=self.browse_file,
            height=45,
            width=120,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        browse_btn.grid(row=0, column=2, padx=10, pady=15)
        self.extract_btn = ctk.CTkButton(
            file_frame,
            text="🔍 提取 URL Schemes",
            command=self.extract_from_local,
            height=45,
            width=180,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2B7A0B",
            hover_color="#205A08"
        )
        self.extract_btn.grid(row=0, column=3, padx=10, pady=15)

        # 应用信息显示区域
        self.make_label(
            main_container,
            "📋 应用信息",
            size=16,
            bold=True
        ).grid(row=2, column=0, padx=30, pady=(15, 5), sticky="w")
        self.info_frame = ctk.CTkFrame(main_container, height=200)
        self.info_frame.grid(row=3, column=0, padx=30, pady=(0, 15), sticky="nsew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        self.create_info_display()

        # URL Schemes 结果区域
        self.make_label(
            main_container,
            "🔗 提取的 URL Schemes",
            size=16,
            bold=True
        ).grid(row=4, column=0, padx=30, pady=(15, 5), sticky="w")
        self.result_frame = ctk.CTkScrollableFrame(main_container)
        self.result_frame.grid(row=5, column=0, padx=30, pady=(0, 15), sticky="nsew")
        self.result_frame.grid_columnconfigure(0, weight=1)

        # 操作按钮区域
        button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        button_frame.grid(row=6, column=0, padx=30, pady=(0, 25))
        self.copy_all_btn = ctk.CTkButton(
            button_frame,
            text="📋 复制全部",
            command=self.copy_all_schemes,
            state="disabled",
            height=40,
            width=140,
            font=ctk.CTkFont(size=14)
        )
        self.copy_all_btn.grid(row=0, column=0, padx=8)
        self.export_btn = ctk.CTkButton(
            button_frame,
            text="💾 导出 JSON",
            command=self.export_to_json,
            state="disabled",
            height=40,
            width=140,
            font=ctk.CTkFont(size=14)
        )
        self.export_btn.grid(row=0, column=1, padx=8)
        self.clear_btn = ctk.CTkButton(
            button_frame,
            text="🗑️ 清空结果",
            command=self.clear_results,
            height=40,
            width=140,
            font=ctk.CTkFont(size=14),
            fg_color="#8B0000",
            hover_color="#660000"
        )
        self.clear_btn.grid(row=0, column=2, padx=8)

    # 创建应用信息显示区域
    def create_info_display(self):
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        # 创建三行标签区域
        labels_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        labels_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 占位文本或实际应用信息展示
        info = self.current_app_info or {}
        display_texts = [
            f"应用名称: {info.get('app_name', '未加载' if not info else info.get('app_name', 'Unknown'))}",
            f"Bundle ID: {info.get('bundle_id', '未加载' if not info else info.get('bundle_id', 'Unknown'))}",
            f"版本: {info.get('version', '未加载' if not info else info.get('version', 'Unknown'))} (Build {info.get('build', '未加载' if not info else info.get('build', 'Unknown'))})"
        ]

        for txt in display_texts:
            self.make_label(
                labels_frame,
                text=txt,
                size=info_size,
                color="gray" if not self.current_app_info else None,
                height=info_height
            ).pack(fill="both", expand=True)

    # 外观样式变更响应
    def change_appearance_mode(self, mode):
        ctk.set_appearance_mode(mode)

    # 文件浏览弹窗
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="选择 IPA 文件",
            filetypes=[("IPA 文件", "*.ipa"), ("所有文件", "*.*")]
        )
        if filename:
            self.file_path_entry.configure(state="normal")
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, filename)
            self.file_path_entry.configure(state="readonly")

    # 从本地 IPA 文件提取信息
    def extract_from_local(self):
        file_path = self.file_path_entry.get()
        if not file_path:
            messagebox.showwarning("警告", "请先选择 IPA 文件")
            return
        if not os.path.exists(file_path):
            messagebox.showerror("错误", "文件不存在")
            return

        self.extract_btn.configure(state="disabled")

        def task():
            plist_data = self.extractor.extract_info_plist(file_path)
            self.current_app_info = self.extractor.extract_app_info(plist_data)
            url_schemes = self.extractor.extract_url_schemes(plist_data)

            self.after(0, self.create_info_display)
            self.after(0, lambda: self.display_schemes(url_schemes))

            if url_schemes:
                self.after(0, lambda: self.copy_all_btn.configure(state="normal"))
                self.after(0, lambda: self.export_btn.configure(state="normal"))
                self.after(0, lambda: messagebox.showinfo(
                    "提取成功",
                    f"成功提取 {len(url_schemes)} 个 URL Scheme"
                ))
            else:
                self.after(0, lambda: messagebox.showinfo(
                    "提取完成",
                    "该应用未包含 URL Scheme"
                ))

            self.after(0, lambda: self.extract_btn.configure(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    # 显示URL Schemes结果
    def display_schemes(self, schemes):
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        self.current_schemes = schemes

        if not schemes:
            self.make_label(
                self.result_frame,
                text="未找到 URL Scheme",
                size=14,
                color="gray"
            ).grid(row=0, column=0, pady=30)
            return

        for i, scheme in enumerate(schemes):
            scheme_frame = ctk.CTkFrame(self.result_frame)
            scheme_frame.grid(row=i, column=0, padx=10, pady=8, sticky="ew")
            scheme_frame.grid_columnconfigure(1, weight=1)

            self.make_label(
                scheme_frame,
                text=f"{i + 1}",
                size=15,
                bold=True,
                height=40
            ).grid(row=0, column=0, padx=(15, 10), pady=12)

            scheme_entry = ctk.CTkEntry(
                scheme_frame,
                font=ctk.CTkFont(size=14),
                height=40
            )
            scheme_entry.insert(0, scheme + "://")
            scheme_entry.configure(state="readonly")
            scheme_entry.grid(row=0, column=1, padx=10, pady=12, sticky="ew")

            copy_btn = ctk.CTkButton(
                scheme_frame,
                text="📋 复制",
                width=80,
                height=40,
                command=lambda s=scheme: self.copy_single_scheme(s)
            )
            copy_btn.grid(row=0, column=2, padx=(10, 15), pady=12)

    # 复制单个Scheme到剪贴板
    def copy_single_scheme(self, scheme):
        self.clipboard_clear()
        self.clipboard_append(scheme + "://")
        messagebox.showinfo("成功", f"已复制: {scheme}" + "://")

    # 复制全部Scheme到剪贴板
    def copy_all_schemes(self):
        if not self.current_schemes:
            return
        content = "\n".join(self.current_schemes)
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo(
            "成功",
            f"已复制 {len(self.current_schemes)} 个 URL Scheme"
        )

    # 导出Scheme结果为JSON
    def export_to_json(self):
        if not self.current_schemes:
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialfile=f"{self.current_app_info.get('app_name', 'app')}_url_schemes.json"
        )
        if filename:
            data = {
                "app_info": self.current_app_info,
                "url_schemes": self.current_schemes,
                "count": len(self.current_schemes)
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("成功", f"已导出到: {filename}")

    # 清空所有结果和状态
    def clear_results(self):
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        self.current_schemes = []
        self.current_app_info = {}
        self.copy_all_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.file_path_entry.configure(state="normal")
        self.file_path_entry.delete(0, "end")
        self.file_path_entry.configure(state="readonly")
        self.create_info_display()


if __name__ == "__main__":
    app = ModernIPAToolApp()
    app.mainloop()
