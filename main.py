
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QListWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextBrowser, QApplication
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QSlider
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QListWidgetItem

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
    """超分功能模块（含医学图像查看功能）"""
    MODULE_NAME = "超分辨率重建"
    ICON = "icon_sr.png"

    def __init__(self):
        super().__init__()
        self.image_data = None  # 存储加载的图像数据（numpy数组）
        self.current_slice = 0  # 当前显示切片序号
        self.orientation = 0  # 显示方向（0:轴向 1:矢状 2:冠状）
        self.image_shape = None
        self.rotation_angle = 0  # 旋转角度（0, 90, 180, 270）

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # 文件拖放区域
        self.drop_label = QLabel("拖放医学图像文件至此（支持.nii.gz/.dcm）")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel { 
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 25px;
                font-size: 14px;
            }
        """)
        self.drop_label.setAcceptDrops(True)

        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(512, 512)

        # 控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout()

        # 方向选择
        self.orient_combo = QComboBox()
        self.orient_combo.addItems(["轴向", "矢状", "冠状"])
        self.orient_combo.currentIndexChanged.connect(self.init_slider)
        self.orient_combo.currentIndexChanged.connect(self.update_display)

        # 切片滑块
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.valueChanged.connect(self.update_display)

        # 当前切片显示
        self.slice_label = QLabel("切片: 0/0")

        # 顺时针和逆时针旋转按钮
        self.rotate_left_button = QPushButton("逆时针旋转")
        self.rotate_right_button = QPushButton("顺时针旋转")

        # 按钮连接
        self.rotate_left_button.clicked.connect(self.rotate_left)
        self.rotate_right_button.clicked.connect(self.rotate_right)

        control_layout.addWidget(QLabel("方向:"))
        control_layout.addWidget(self.orient_combo)
        control_layout.addWidget(QLabel("切片:"))
        control_layout.addWidget(self.slice_slider)
        control_layout.addWidget(self.slice_label)
        control_layout.addWidget(self.rotate_left_button)  # 逆时针旋转按钮
        control_layout.addWidget(self.rotate_right_button)  # 顺时针旋转按钮

        control_panel.setLayout(control_layout)

        self.layout.addWidget(self.drop_label)
        self.layout.addWidget(self.image_label)
        self.layout.addWidget(control_panel)

        self.drop_label.dragEnterEvent = self.dragEnterEvent
        self.drop_label.dropEvent = self.dropEvent

    # 添加拖放支持
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            if filepath.endswith(('.nii.gz', '.dcm')):
                self.load_medical_image(filepath)
                break

    def load_medical_image(self, filepath):
        """加载医学图像文件"""
        try:
            if filepath.endswith('.nii.gz'):
                import nibabel as nib
                img = nib.load(filepath)
                self.image_data = img.get_fdata()

            elif filepath.endswith('.dcm'):
                import pydicom
                ds = pydicom.dcmread(filepath)
                self.image_data = ds.pixel_array

            self.image_shape = self.image_data.shape
            print("image_data_shape:", str(self.image_shape))

            self.init_slider()

            self.update_display()

        except Exception as e:
            self.drop_label.setText(f"加载失败: {str(e)}")

    def init_slider(self):
        """初始化切片滑块"""
        self.orientation = self.orient_combo.currentIndex()
        depth = self.image_data.shape[self.orientation]
        self.slice_slider.setRange(0, depth - 1)
        self.slice_slider.setValue(0)
        self.slice_label.setText(f"切片: 0/{depth - 1}")

    def update_display(self):
        """更新图像显示"""
        if self.image_data is None:
            return

        self.current_slice = self.slice_slider.value()
        self.orientation = self.orient_combo.currentIndex()

        try:
            # 提取切片
            if self.orientation == 0:  # 轴向
                slice_data = self.image_data[self.current_slice, :, :]
            elif self.orientation == 1:  # 矢状
                slice_data = self.image_data[:, self.current_slice, :]
            else:  # 冠状
                slice_data = self.image_data[:, :, self.current_slice]

            # 旋转切片
            if self.rotation_angle == 90:
                slice_data = np.rot90(slice_data, k=1)
            elif self.rotation_angle == 180:
                slice_data = np.rot90(slice_data, k=2)
            elif self.rotation_angle == 270:
                slice_data = np.rot90(slice_data, k=3)

            print("slice_data.shape:", str(slice_data.shape))
            # 转换为QImage
            import matplotlib.pyplot as plt
            # 确保 slice_data 是 numpy 数组并且是二维的
            if not isinstance(slice_data, np.ndarray):
                raise ValueError("slice_data is not a numpy array")
            if len(slice_data.shape) != 2:
                raise ValueError("slice_data is not 2D")

            # 使用 matplotlib 生成图像并保存
            plt.figure(figsize=(5, 5))
            plt.imshow(slice_data.T, cmap='gray', origin='lower')  # 转置图像以符合显示习惯
            plt.axis('off')
            plt.tight_layout()

            # 使用 'tight' 让 matplotlib 自动调整边界
            plt.savefig("temp_slice.png", bbox_inches='tight')

            # 显示图像
            pixmap = QPixmap("temp_slice.png")
            self.image_label.setPixmap(pixmap.scaled(512, 512, Qt.KeepAspectRatio))

            # 更新切片标签
            depth = self.image_data.shape[self.orientation]
            self.slice_label.setText(f"切片: {self.current_slice}/{depth - 1}")
        except Exception as e:
            print(f"更新显示失败: {str(e)}")
            print("详细错误信息：")
            traceback.print_exc()

    def rotate_left(self):
        """逆时针旋转图像"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.update_display()

    def rotate_right(self):
        """顺时针旋转图像"""
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.update_display()


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