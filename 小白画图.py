import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
from PIL import ImageGrab, Image, ImageTk, ImageDraw
import tempfile
import os

class FlatButton(tk.Canvas):
    """自定义圆角扁平化按钮"""
    def __init__(self, master, text, command, bg="#0078d4", fg="white", width=80, height=30):
        super().__init__(master, width=width, height=height, highlightthickness=0)
        self.command = command
        self.bg = bg
        self.fg = fg
        
        # 绘制圆角矩形
        self.create_round_rect(0, 0, width, height, radius=5, fill=bg, tags="bg")
        self.create_text(width // 2, height // 2, text=text, fill=fg, font=('微软雅黑', 10))
        
        # 绑定事件
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def create_round_rect(self, x1, y1, x2, y2, radius=5, **kwargs):
        """创建圆角矩形"""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2, x1, y2 - radius,
            x1, y1 + radius, x1, y1,
            x1 + radius, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

    def on_click(self, event):
        self.itemconfig("bg", fill=self.darken_color(self.bg))
        self.command()
        self.after(100, lambda: self.itemconfig("bg", fill=self.bg))

    def on_enter(self, event):
        self.itemconfig("bg", fill=self.darken_color(self.bg, 20))

    def on_leave(self, event):
        self.itemconfig("bg", fill=self.bg)

    def darken_color(self, hex_color, percent=30):
        """颜色加深处理"""
        hex_color = hex_color.lstrip('#')
        rgb = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
        return "#{:02x}{:02x}{:02x}".format(
            *[max(0, int(c * (100 - percent) / 100)) for c in rgb]
        )

class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("小白画图")
        
        # 初始化参数
        self.pen_color = "black"
        self.pen_size = 2
        self.tool_mode = "pen"
        self.history = []  # 内存中的历史记录
        self.cache_files = []  # 缓存文件列表
        self.history_index = -1  # 当前历史索引
        self.cache_dir = tempfile.mkdtemp()
        self.MAX_MEMORY_STATES = 5
        
        # 创建顶部工具栏
        toolbar = tk.Frame(root, bg="#f0f0f0", height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # 文件操作按钮
        self.open_btn = FlatButton(toolbar, "打开", self.open_image, width=60)
        self.open_btn.pack(side=tk.LEFT, padx=3)
        
        # 工具按钮
        self.pen_btn = FlatButton(toolbar, "画笔", lambda: self.set_tool("pen"), width=60)
        self.pen_btn.pack(side=tk.LEFT, padx=3)
        
        self.eraser_btn = FlatButton(toolbar, "橡皮擦", lambda: self.set_tool("eraser"), width=60)
        self.eraser_btn.pack(side=tk.LEFT, padx=3)
        
        self.bucket_btn = FlatButton(toolbar, "墨桶", lambda: self.set_tool("bucket"), width=60)
        self.bucket_btn.pack(side=tk.LEFT, padx=3)
        
        # 颜色选择按钮
        self.color_btn = FlatButton(toolbar, "颜色", self.choose_color, width=60)
        self.color_btn.pack(side=tk.LEFT, padx=3)
        
        # 笔刷大小滑块
        self.size_scale = tk.Scale(toolbar, from_=1, to=20, orient=tk.HORIZONTAL,
                                   sliderrelief="flat", troughcolor="#e0e0e0",
                                   highlightthickness=0, length=120,
                                   command=lambda v: self.change_size(v))
        self.size_scale.set(self.pen_size)
        self.size_scale.pack(side=tk.LEFT, padx=5)
        
        # 撤销/重做按钮
        self.undo_btn = FlatButton(toolbar, "撤销", self.undo, width=60)
        self.undo_btn.pack(side=tk.LEFT, padx=3)
        self.redo_btn = FlatButton(toolbar, "回退", self.redo, width=60)
        self.redo_btn.pack(side=tk.LEFT, padx=3)
        
        # 其他功能按钮
        self.clear_btn = FlatButton(toolbar, "清除", self.clear_canvas, width=60)
        self.clear_btn.pack(side=tk.LEFT, padx=3)
        self.save_btn = FlatButton(toolbar, "保存", self.save_image, width=60)
        self.save_btn.pack(side=tk.LEFT, padx=3)
        
        # 创建画布
        self.canvas = tk.Canvas(root, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定事件
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.reset)
        self.old_x = None
        self.old_y = None

    def set_tool(self, tool):
        """切换工具模式"""
        self.tool_mode = tool
        if tool == "eraser":
            self.pen_color = "white"

    def choose_color(self):
        """选择颜色"""
        color = colorchooser.askcolor(title="选择颜色")[1]
        if color:
            self.pen_color = color
            self.set_tool("pen")

    def change_size(self, value):
        """调整笔刷大小"""
        self.pen_size = int(value)

    def on_click(self, event):
        """鼠标点击事件处理"""
        if self.tool_mode == "bucket":
            self.flood_fill(event.x, event.y)
        else:
            self.old_x = event.x
            self.old_y = event.y

    def on_drag(self, event):
        """鼠标拖动事件处理"""
        if self.tool_mode in ["pen", "eraser"]:
            self.draw(event)

    def draw(self, event):
        """绘制线条"""
        color = self.pen_color if self.tool_mode == "pen" else "white"
        if self.old_x and self.old_y:
            self.canvas.create_line(
                self.old_x, self.old_y, event.x, event.y,
                width=self.pen_size, fill=color,
                capstyle=tk.ROUND, smooth=True
            )
        self.old_x = event.x
        self.old_y = event.y

    def flood_fill(self, x, y):
        """改进的油漆桶填充功能"""
        try:
            # 获取画布内容
            canvas_x = self.canvas.winfo_rootx()
            canvas_y = self.canvas.winfo_rooty()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # 截取画布区域
            bbox = (
                canvas_x,
                canvas_y,
                canvas_x + canvas_width,
                canvas_y + canvas_height
            )
            img = ImageGrab.grab(bbox=bbox).convert("RGB")

            # 转换点击坐标为图像坐标
            img_x = x  # 画布内相对坐标
            img_y = y  # 画布内相对坐标

            # 调试信息
            print(f"填充坐标：画布内({x},{y})，图像({img_x},{img_y})")
            print(f"图像尺寸：{img.size}，画布尺寸：{canvas_width}x{canvas_height}")

            # 执行填充
            ImageDraw.floodfill(img, (img_x, img_y), self.pen_color, thresh=50)

            # 更新画布显示
            self.save_state()
            self.update_canvas(img)
            
        except Exception as e:
            messagebox.showerror("错误", f"填充失败: {str(e)}")

    def update_canvas(self, img):
        """更新画布显示"""
        self.canvas.delete("all")
        photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        self.canvas.image = photo

    def reset(self, event):
        """记录操作状态"""
        if self.tool_mode in ["pen", "eraser"]:
            self.save_state()
        self.old_x = None
        self.old_y = None

    def save_state(self):
        """保存当前画布状态"""
        # 移除未来的历史记录
        if self.history_index < len(self.history) + len(self.cache_files) - 1:
            overflow = len(self.history) + len(self.cache_files) - 1 - self.history_index
            self.cache_files = self.cache_files[:len(self.cache_files) - overflow]
            self.history = self.history[:self.history_index + 1 - len(self.cache_files)]

        # 获取精确画布区域
        canvas_x = self.root.winfo_rootx() + self.canvas.winfo_x()
        canvas_y = self.root.winfo_rooty() + self.canvas.winfo_y()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        bbox = (
            canvas_x,
            canvas_y,
            canvas_x + canvas_width,
            canvas_y + canvas_height
        )
        img = ImageGrab.grab(bbox=bbox).convert("RGB")

        # 管理历史记录
        if len(self.history) >= self.MAX_MEMORY_STATES:
            # 转移最早记录到缓存
            cache_path = os.path.join(self.cache_dir, f"cache_{len(self.cache_files)}.png")
            self.history[0].save(cache_path)
            self.cache_files.append(cache_path)
            self.history.pop(0)

        self.history.append(img)
        self.history_index = len(self.history) + len(self.cache_files) - 1

    def restore_state(self):
        """恢复指定历史状态"""
        total = len(self.history) + len(self.cache_files)
        if self.history_index < 0 or self.history_index >= total:
            return

        # 加载记录
        if self.history_index < len(self.history):
            img = self.history[self.history_index]
        else:
            cache_index = self.history_index - len(self.history)
            try:
                img = Image.open(self.cache_files[cache_index])
            except:
                return

        # 更新画布
        self.update_canvas(img)

    def undo(self):
        """撤销操作"""
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state()

    def redo(self):
        """重做操作"""
        if self.history_index < len(self.history) + len(self.cache_files) - 1:
            self.history_index += 1
            self.restore_state()

    def open_image(self):
        """打开图片文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if file_path:
            try:
                img = Image.open(file_path)
                img = img.resize((800, 600), Image.Resampling.LANCZOS)
                self.save_state()
                self.update_canvas(img)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开图片: {str(e)}")

    def clear_canvas(self):
        """清除画布"""
        self.save_state()
        self.canvas.delete("all")

    def save_image(self):
        """保存图片"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG文件", "*.png"), ("所有文件", "*.*")]
        )
        if file_path:
            canvas_x = self.root.winfo_rootx() + self.canvas.winfo_x()
            canvas_y = self.root.winfo_rooty() + self.canvas.winfo_y()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            bbox = (
                canvas_x,
                canvas_y,
                canvas_x + canvas_width,
                canvas_y + canvas_height
            )
            img = ImageGrab.grab(bbox=bbox)
            img.save(file_path)
            messagebox.showinfo("提示", "图片保存成功！")

    def __del__(self):
        """清理缓存"""
        if os.path.exists(self.cache_dir):
            for f in self.cache_files:
                try:
                    os.remove(f)
                except:
                    pass
            try:
                os.rmdir(self.cache_dir)
            except:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = DrawingApp(root)
    root.mainloop()