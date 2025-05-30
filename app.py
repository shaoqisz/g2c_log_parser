import sys
import json
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, 
                            QMessageBox, QTableWidget, QTableWidgetItem, 
                            QHeaderView, QGroupBox, QFormLayout, QScrollArea, QSplitter,
                            QFileDialog)
from PyQt5.QtGui import QIcon

class HexParser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G2C Log Parser")
        self.setGeometry(100, 100, 1000, 800)
        self.setWindowIcon(QIcon('app.ico'))
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 使用 QSplitter 分割三个区域
        splitter = QSplitter(QtCore.Qt.Vertical)
        main_layout.addWidget(splitter)

        # 设置QSplitter样式使其可见
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: gray;
                height: 1px;
            }
        """)
        splitter.setChildrenCollapsible(False)  # 禁止子部件折叠

        # ------------------------- Part 1: 输入区域 -------------------------
        part1_widget = QWidget()
        part1_layout = QVBoxLayout(part1_widget)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("请输入数据包内容（格式：字节序号:值 用空格/Tab分隔）")
        part1_layout.addWidget(self.input_text)
        splitter.addWidget(part1_widget)

        # ------------------------- Part 2: 配置区域 -------------------------
        part2_widget = QWidget()
        part2_layout = QVBoxLayout(part2_widget)
        
        # 配置滚动区域
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_widget = QWidget()
        self.config_layout = QVBoxLayout(config_widget)
        config_scroll.setWidget(config_widget)
        part2_layout.addWidget(config_scroll)
        
        # 添加配置按钮
        self.add_config_btn = QPushButton("添加字段")
        self.add_config_btn.clicked.connect(self.add_default_config_group)
        
        # 保存/加载按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_configs)
        self.load_btn = QPushButton("加载配置")
        self.load_btn.clicked.connect(self.load_configs)
        btn_layout.addWidget(self.add_config_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        part2_layout.addLayout(btn_layout)
        
        splitter.addWidget(part2_widget)

        # ------------------------- Part 3: 结果区域 -------------------------
        part3_widget = QWidget()
        part3_layout = QVBoxLayout(part3_widget)
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(7)  # 新增一列显示配置名称
        self.result_table.setHorizontalHeaderLabels(["字段ID", "字段名称", "字节范围", "字节序", "字节值", "十六进制", "整数值"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        part3_layout.addWidget(self.result_table)
        
        self.parse_btn = QPushButton("解析所有字段")
        self.parse_btn.clicked.connect(self.parse_all)
        part3_layout.addWidget(self.parse_btn)
        
        splitter.addWidget(part3_widget)

        # 设置初始分割比例
        splitter.setSizes([1, 2, 3])
        
        # 初始化配置组
        self.config_groups = []
        self.add_default_config_group()

    def add_default_config_group(self):
        """添加默认的解析配置组"""
        self.add_config_group('', '0-3', 'little')

    # ------------------------- 配置管理功能 -------------------------
    def add_config_group(self, name, range, endian):
        group_id = len(self.config_groups) + 1
        
        group_box = QGroupBox(f"字段 {group_id}")
        # group_box.setCheckable(True)
        form_layout = QFormLayout()
        
        # 配置名称输入
        name_edit = QLineEdit(name if name else f"字段 {group_id}")
        # name_edit.textChanged.connect(lambda text, box=group_box: box.setTitle(text if text else f"解析配置 {group_id}"))
        form_layout.addRow("字段名称：", name_edit)
        
        # 字节范围输入
        range_edit = QLineEdit(range)
        form_layout.addRow("字节范围（起始-结束）：", range_edit)
        
        # 字节序选择
        endian_layout = QHBoxLayout()
        big_endian = QRadioButton("大端序")
        little_endian = QRadioButton("小端序")
        if endian == 'little':
            little_endian.setChecked(True)
            big_endian.setChecked(False)
        else:
            big_endian.setChecked(True)
            little_endian.setChecked(False)

        endian_layout.addWidget(big_endian)
        endian_layout.addWidget(little_endian)
        form_layout.addRow("字节序：", endian_layout)
        
        # 删除按钮
        delete_btn = QPushButton("删除字段")
        delete_btn.setMaximumWidth(200)  # 设置按钮最大宽度
        delete_btn.clicked.connect(lambda _, box=group_box: self.remove_config_group(box))
        # form_layout.addRow(delete_btn)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(delete_btn)
        button_layout.setContentsMargins(0, 0, 0, 0)  # 顶部和右侧边距
        
        form_layout.addRow(button_layout)
        
        group_box.setLayout(form_layout)
        self.config_layout.addWidget(group_box)
        
        # 创建配置数据结构
        config = {
            'group_box': group_box,
            'name_edit': name_edit,
            'range_edit': range_edit,
            'endian': endian,
            'endian_widgets': (big_endian, little_endian)
        }
        
        # 连接信号
        big_endian.toggled.connect(lambda state, c=config: self._update_endian(state, c, "big"))
        little_endian.toggled.connect(lambda state, c=config: self._update_endian(state, c, "little"))
        
        self.config_groups.append(config)
        
    def _update_endian(self, state, config, endian_value):
        """更新配置中的字节序值"""
        if state:  # 仅处理选中状态
            config['endian'] = endian_value
            
    def remove_config_group(self, group_box):
        """删除指定的配置组"""
        for i, config in enumerate(self.config_groups):
            if config['group_box'] == group_box:
                self.config_layout.removeWidget(group_box)
                group_box.deleteLater()
                self.config_groups.pop(i)
                self.update_config_group_labels()
                break
                
    def update_config_group_labels(self):
        """更新配置组标签"""
        for i, config in enumerate(self.config_groups):
            name = config['name_edit'].text()
            config['group_box'].setTitle(f"字段 {i+1}")

    # ------------------------- 解析功能 -------------------------
    def parse_all(self):
        """解析所有配置"""
        input_data = self.input_text.toPlainText().strip()
        if not input_data:
            QMessageBox.warning(self, "警告", "请输入数据包内容")
            return
            
        try:
            bytes_data = self._parse_bytes(input_data)
            if not bytes_data:
                QMessageBox.warning(self, "解析错误", "未能解析任何字节数据")
                return
                
            self.result_table.setRowCount(0)
            
            for i, config in enumerate(self.config_groups):
                try:
                    # 获取配置参数
                    name = config['name_edit'].text() or f"字段 {i+1}"
                    range_text = config['range_edit'].text().strip()
                    start, end = map(int, range_text.split('-'))
                    endian = config['endian']
                    
                    # 提取字节并转换
                    selected_bytes = [bytes_data[j] for j in range(start, end+1)]
                    value = int.from_bytes(selected_bytes, byteorder=endian)
                    
                    # 显示结果
                    row = self.result_table.rowCount()
                    self.result_table.insertRow(row)
                    self.result_table.setItem(row, 0, QTableWidgetItem(str(i+1)))
                    self.result_table.setItem(row, 1, QTableWidgetItem(name))  # 新增配置名称列
                    self.result_table.setItem(row, 2, QTableWidgetItem(f"{start}-{end}"))
                    self.result_table.setItem(row, 3, QTableWidgetItem("小端序" if endian == "little" else "大端序"))
                    self.result_table.setItem(row, 4, QTableWidgetItem(" ".join([f"0x{b:02x}" for b in selected_bytes])))
                    self.result_table.setItem(row, 5, QTableWidgetItem(f"0x{value:X}"))
                    self.result_table.setItem(row, 6, QTableWidgetItem(str(value)))
                    
                except Exception as e:
                    QMessageBox.warning(self, "配置错误", f"字段 {i+1} ({name}) 解析失败：{str(e)}")
                    continue

        except Exception as e:
            QMessageBox.critical(self, "系统错误", f"解析过程中发生错误：{str(e)}")

    def _parse_bytes(self, data):
        """解析输入数据为字节字典"""
        bytes_dict = {}
        lines = data.split('\n')
        
        for line in lines:
            line = line.split('***')[-1].strip()
            items = line.split()
            for item in items:
                try:
                    if ':' in item:
                        index, value = item.split(':')
                        byte_index = int(index.strip().split(':')[-1])
                        byte_value = int(value, 16)
                        bytes_dict[byte_index] = byte_value
                except:
                    continue
        return bytes_dict

    # ------------------------- 配置存储功能 -------------------------
    def save_configs(self):
        """保存配置到JSON文件"""
        configs = []
        for config in self.config_groups:
            config_data = {
                "name": config['name_edit'].text(),
                "range": config['range_edit'].text(),
                "endian": config['endian']
            }
            configs.append(config_data)
        
        file_path, _ = QFileDialog.getSaveFileName(self, "保存配置", "", "JSON文件 (*.json)")
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(configs, f, indent=2)
                QMessageBox.information(self, "保存成功", f"配置已保存到：\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存配置时发生错误：{str(e)}")

    def load_configs(self):
        """从JSON文件加载配置"""
        file_path, _ = QFileDialog.getOpenFileName(self, "加载配置", "", "JSON文件 (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    configs = json.load(f)
                
                # 清空现有配置
                for config in self.config_groups:
                    config['group_box'].deleteLater()
                self.config_groups = []
                # self.config_layout.deleteLater()
                # self.config_layout = QVBoxLayout()
                
                # 重新创建配置组
                for idx, config_data in enumerate(configs, 1):
                    self.add_config_group(config_data.get("name", f"字段 {idx}"), config_data.get("range", "0-3"), config_data.get("endian", "little"))

                # QMessageBox.information(self, "加载成功", f"已从以下文件加载配置：\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"加载配置时发生错误：{str(e)}")
                # 恢复原有配置
                self.reset_configs()

    def reset_configs(self):
        """重置配置（用于加载失败时恢复）"""
        for config in self.config_groups:
            config['group_box'].deleteLater()
        self.config_groups = []
        self.add_default_config_group()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HexParser()
    window.show()
    sys.exit(app.exec_())