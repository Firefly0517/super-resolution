
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QListWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextBrowser, QCheckBox, QApplication
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QSlider
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import QLineEdit
from PySide6.QtGui import QIntValidator

import sys
import json
import traceback
import numpy as np

class BaseModule(QWidget):
    """所有功能模块的基类"""
    MODULE_NAME = "Base Module"
    ICON = "icon_default.png"

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """子类需要重写此方法"""
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Module Content Area")
        self.layout.addWidget(self.label)


class SRModule(BaseModule):
    MODULE_NAME = "多模态超分对比"
    ICON = "icon_sr.png"

    def __init__(self):
        super().__init__()
        self.image_data = {
            "low_res": None,  # 低分辨率图像
            "high_res": None  # 高分辨率参考图像
        }
        self.current_settings = {
            "low_res": {"slice": 0, "orientation": 0, "rotation": 0},
            "high_res": {"slice": 0, "orientation": 0, "rotation": 0}
        }
        self.sync_controls = True  # 是否同步控制

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # 创建双视图容器
        views_container = QWidget()
        views_layout = QHBoxLayout(views_container)

        # 初始化两个独立视图
        views_layout.addWidget(self.create_view("低分辨率图像", "low_res"))
        views_layout.addWidget(self.create_view("高分辨率参考", "high_res"))

        self.layout.addWidget(views_container)

    def create_view(self, title, modality):
        """创建包含独立控制的视图"""
        container = QWidget()
        layout = QVBoxLayout(container)

        # 标题标签
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)

        # 拖放区域
        drop_label = DropTargetLabel(modality)
        drop_label.setAcceptDrops(True)
        drop_label.filesDropped.connect(self.load_image)

        # 图像显示区域
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumSize(400, 400)
        image_label.setStyleSheet("background: #333;")

        # 独立控制面板
        control_panel = self.create_control_panel(modality)

        layout.addWidget(title_label)
        layout.addWidget(drop_label)
        layout.addWidget(image_label)
        layout.addWidget(control_panel)

        # 保存组件引用
        setattr(self, f"{modality}_drop", drop_label)
        setattr(self, f"{modality}_display", image_label)

        return container

    def create_control_panel(self, modality):
        """创建包含输入框和滑块的控制面板"""
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 第一行：切片输入与滑块
        slice_row = QHBoxLayout()

        # 输入框
        self.slice_input = QLineEdit()
        self.slice_input.setFixedWidth(80)
        self.slice_input.setValidator(QIntValidator())  # 限制只能输入整数

        slice_label = QLabel("切片: 0/0")  # 创建切片标签
        setattr(self, f"{modality}_slice_label", slice_label)


        # 滑块
        slice_slider = QSlider(Qt.Horizontal)

        slice_row.addWidget(QLabel("切片位置:"))
        slice_row.addWidget(self.slice_input)
        slice_row.addWidget(slice_slider)

        # 第二行：操作控制
        control_row = QHBoxLayout()

        # 方向选择
        orient_combo = QComboBox()
        orient_combo.addItems(["轴向", "矢状", "冠状"])

        # 旋转按钮
        rotate_box = QHBoxLayout()
        rotate_left = QPushButton("↺ 逆时针")
        rotate_right = QPushButton("↻ 顺时针")

        rotate_box.addWidget(rotate_left)
        rotate_box.addWidget(rotate_right)

        control_row.addWidget(QLabel("方向:"))
        control_row.addWidget(orient_combo)
        control_row.addStretch()
        control_row.addLayout(rotate_box)

        # 添加行布局
        main_layout.addLayout(slice_row)
        main_layout.addLayout(control_row)

        slice_row.addWidget(QLabel("切片位置:"))
        slice_row.addWidget(self.slice_input)
        slice_row.addWidget(slice_slider)
        slice_row.addWidget(slice_label)

        # 信号连接
        orient_combo.currentIndexChanged.connect(
            lambda idx: self.update_orientation(modality, idx)
        )
        slice_slider.valueChanged.connect(
            lambda val: self.update_slice(modality, val)
        )
        rotate_left.clicked.connect(
            lambda: self.rotate_image(modality, 90)
        )
        rotate_right.clicked.connect(
            lambda: self.rotate_image(modality, -90)
        )
        slice_slider.valueChanged.connect(
            lambda val: self.on_slider_changed(modality, val)
        )
        self.slice_input.returnPressed.connect(
            lambda: self.on_input_changed(modality)
        )

        # 保存控件引用
        setattr(self, f"{modality}_slider", slice_slider)
        setattr(self, f"{modality}_input", self.slice_input)
        setattr(self, f"{modality}_slice_label", slice_label)

        return panel

    def load_image(self, modality, filepath):
        """加载医学图像"""
        try:
            # 根据文件后缀选择加载方式
            if filepath.endswith('.nii.gz'):
                import nibabel as nib
                img = nib.load(filepath)
                self.image_data[modality] = img.get_fdata()
            elif filepath.endswith('.dcm'):
                import pydicom
                ds = pydicom.dcmread(filepath)
                self.image_data[modality] = ds.pixel_array

            # 更新显示
            self.update_display(modality)
            self.update_slider_range()

        except Exception as e:
            getattr(self, f"{modality}_drop").setText(f"加载失败: {str(e)}")

    def update_display(self, modality):
        """更新单个模态显示"""
        data = self.image_data[modality]
        if data is None:
            return

        settings = self.current_settings[modality]

        # 提取切片
        orientation = settings["orientation"]
        slice_idx = settings["slice"]

        if orientation == 0:  # 轴向
            slice_data = data[slice_idx, :, :]
        elif orientation == 1:  # 矢状
            slice_data = data[:, slice_idx, :]
        else:  # 冠状
            slice_data = data[:, :, slice_idx]

        # 应用旋转
        if settings["rotation"] != 0:
            slice_data = np.rot90(slice_data, k=settings["rotation"] // 90)

        # 显示切片
        self.display_slice(modality, slice_data)

    def display_slice(self, modality, slice_data):
        """使用Matplotlib显示单个切片"""
        try:
            import matplotlib.pyplot as plt

            # 确保数据合法性
            if not isinstance(slice_data, np.ndarray) or slice_data.ndim != 2:
                raise ValueError("Invalid slice data")

            # 创建新figure避免内存泄漏
            fig = plt.figure(figsize=(5, 5), dpi=100)
            ax = fig.add_subplot(111)

            # 显示图像（自动应用归一化）
            ax.imshow(slice_data.T,
                      cmap='gray',
                      origin='lower',
                      aspect='equal')  # 保持像素方形比例

            # 隐藏坐标轴
            ax.axis('off')
            plt.tight_layout(pad=0)

            # 生成唯一临时文件名
            temp_file = f"temp_{modality}.png"

            # 保存图像（调整bbox和dpi保证画质）
            plt.savefig(temp_file,
                        bbox_inches='tight',
                        pad_inches=0,
                        dpi=100)
            plt.close(fig)  # 显式关闭figure释放内存

            # 加载并显示图像
            pixmap = QPixmap(temp_file)
            target_label = getattr(self, f"{modality}_display")

            # 保持宽高比缩放
            target_label.setPixmap(
                pixmap.scaled(target_label.size(),
                              Qt.KeepAspectRatio,
                              Qt.SmoothTransformation)
            )

        except Exception as e:
            print(f"显示错误 ({modality}): {str(e)}")
            traceback.print_exc()

    def update_slice(self, modality, value):
        """更新单个模态切片"""
        self.current_settings[modality]["slice"] = value
        data = self.image_data[modality]

        if data is not None:
            orientation = self.current_settings[modality]["orientation"]
            max_slice = data.shape[orientation] - 1
            getattr(self, f"{modality}_slice_label").setText(
                f"切片: {value}/{max_slice}"
            )

        self.update_display(modality)

    def update_orientation(self, modality, index):
        """更新单个模态方向"""
        self.current_settings[modality]["orientation"] = index
        self.update_slider_range(modality)
        self.update_display(modality)


    def rotate_image(self, modality, angle):
        """更新单个模态旋转"""
        current = self.current_settings[modality]["rotation"]
        self.current_settings[modality]["rotation"] = (current + angle) % 360
        self.update_display(modality)

    def update_slider_range(self, modality):
        """根据当前方向更新控件范围"""
        data = self.image_data[modality]
        if data is not None:
            orientation = self.current_settings[modality]["orientation"]
            max_slice = data.shape[orientation] - 1

            # 更新滑块
            slider = getattr(self, f"{modality}_slider")
            slider.setRange(0, max_slice)

            # 更新输入验证
            input_field = getattr(self, f"{modality}_input")
            validator = QIntValidator(0, max_slice)  # 动态设置验证范围
            input_field.setValidator(validator)

            # 更新提示文本
            input_field.setPlaceholderText(f"0-{max_slice}")
            getattr(self, f"{modality}_slice_label").setText(f"切片: 0/{max_slice}")

    def on_slider_changed(self, modality, value):
        """滑块变化时更新输入框"""
        input_field = getattr(self, f"{modality}_input")
        input_field.setText(str(value))
        self.update_slice(modality, value)  # 调用原有的切片更新方法

    def on_input_changed(self, modality):
        """输入框变化时更新滑块"""
        input_field = getattr(self, f"{modality}_input")
        slider = getattr(self, f"{modality}_slider")

        try:
            value = int(input_field.text())
            max_value = slider.maximum()

            # 限制输入范围
            if value < 0:
                value = 0
            elif value > max_value:
                value = max_value

            slider.setValue(value)
            input_field.setText(str(value))  # 更新可能被修正的值
        except ValueError:
            # 输入无效时恢复之前的值
            input_field.setText(str(slider.value()))


class DropTargetLabel(QLabel):
    filesDropped = Signal(str, str)  # (modality, filepath)

    def __init__(self, modality):
        super().__init__("拖放文件至此")
        self.modality = modality
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel { 
                border: 2px dashed #666;
                border-radius: 10px;
                padding: 20px;
                color: #999;
                font-size: 14px;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            if filepath.endswith(('.nii.gz', '.dcm')):
                self.filesDropped.emit(self.modality, filepath)
                self.setText(f"已加载: {filepath.split('/')[-1]}")
                break

class HelpModule(BaseModule):
    """用户手册模块"""
    MODULE_NAME = "用户手册"
    ICON = "icon_help.png"

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.load_help_content()
        self.layout.addWidget(self.browser)

    def load_help_content(self):
        try:
            with open('help_manual.md', 'r') as f:
                self.browser.setMarkdown(f.read())
        except FileNotFoundError:
            self.browser.setText("用户手册文件未找到")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.modules = []
        self.current_module = None
        self.init_ui()
        self.load_modules()

    def init_ui(self):
        # 主界面布局
        main_widget = QWidget()
        self.main_layout = QHBoxLayout(main_widget)

        # 侧边导航栏
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.itemClicked.connect(self.switch_module)

        # 模块容器
        self.stack = QStackedWidget()

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stack)

        self.setCentralWidget(main_widget)
        self.setWindowTitle("医学图像超分系统")
        self.setMinimumSize(800, 600)

    def load_modules(self):
        """动态加载模块"""
        # 注册内置模块
        self.add_module(SRModule())
        self.add_module(HelpModule())

        # 加载扩展模块（示例）
        try:
            with open('extensions.json') as f:
                extensions = json.load(f)
                for ext in extensions:
                    # 此处需要实现动态导入
                    pass
        except Exception as e:
            print(f"扩展加载失败: {str(e)}")

    def add_module(self, module):
        """添加新功能模块"""
        self.modules.append(module)
        self.stack.addWidget(module)

        # 添加导航项
        item = QListWidgetItem(module.MODULE_NAME)
        item.setIcon(QIcon(module.ICON))
        item.setSizeHint(QSize(180, 50))
        self.sidebar.addItem(item)

    def switch_module(self, item):
        """切换功能模块"""
        index = self.sidebar.row(item)
        self.stack.setCurrentIndex(index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())