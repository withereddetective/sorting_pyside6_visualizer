import sys
import random
import time
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QSlider, QLabel, QSpinBox
)
from PySide6.QtGui import QPainter, QColor

ALGORITHMS = {
    "Bubble Sort": "bubble_sort",
    "Selection Sort": "selection_sort",
    "Insertion Sort": "insertion_sort",
    "Merge Sort": "merge_sort",
    "Quick Sort": "quick_sort",
    "Radix Sort": "radix_sort",
}


class SortWorker(QThread):
    # Signals to communicate back to the main GUI thread
    update_signal = Signal(list, int, int, int, int)  # (current_list, active_index_1, active_index_2, reads, writes)
    finished_signal = Signal()

    def __init__(self, data, algorithm, delay):
        super().__init__()
        self.data = data.copy()
        self.algorithm = algorithm
        self.delay = delay
        self._is_running = True
        self.reads = 0
        self.writes = 0

    def run(self):
        algorithm = getattr(self, ALGORITHMS[self.algorithm])
        algorithm()
        
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False

    def sleep_and_check(self):
        time.sleep(self.delay)
        return self._is_running

    def read(self, index):
        self.reads += 1
        return self.data[index]

    def write(self, index, value):
        self.writes += 1
        self.data[index] = value

    def emit_update(self, active_1=-1, active_2=-1):
        self.update_signal.emit(self.data, active_1, active_2, self.reads, self.writes)

    def bubble_sort(self):
        n = len(self.data)
        for i in range(n):
            for j in range(0, n - i - 1):
                if not self._is_running:
                    return
                
                left = self.read(j)
                right = self.read(j + 1)
                if left > right:
                    self.write(j, right)
                    self.write(j + 1, left)
                
                self.emit_update(j, j + 1)
                if not self.sleep_and_check():
                    return

    def selection_sort(self):
        n = len(self.data)
        for i in range(n):
            min_idx = i
            for j in range(i + 1, n):
                if not self._is_running:
                    return
                
                current = self.read(j)
                minimum = self.read(min_idx)
                self.emit_update(j, min_idx)
                if not self.sleep_and_check():
                    return
                
                if current < minimum:
                    min_idx = j
            
            current = self.read(i)
            minimum = self.read(min_idx)
            self.write(i, minimum)
            self.write(min_idx, current)
            self.emit_update(i, min_idx)

    def insertion_sort(self):
        for i in range(1, len(self.data)):
            key = self.read(i)
            j = i - 1
            while j >= 0:
                current = self.read(j)
                if current <= key:
                    break

                if not self._is_running:
                    return
                
                self.write(j + 1, current)
                self.emit_update(j, j + 1)
                if not self.sleep_and_check():
                    return
                j -= 1
            
            self.write(j + 1, key)
            self.emit_update(i, j + 1)

    def merge_sort(self):
        self._merge_sort(0, len(self.data) - 1)

    def _merge_sort(self, left, right):
        if left >= right or not self._is_running:
            return

        middle = (left + right) // 2
        self._merge_sort(left, middle)
        self._merge_sort(middle + 1, right)
        if not self._is_running:
            return

        merged = []
        left_index = left
        right_index = middle + 1

        while left_index <= middle and right_index <= right:
            left_value = self.read(left_index)
            right_value = self.read(right_index)
            if left_value <= right_value:
                merged.append((left_index, left_value))
                left_index += 1
            else:
                merged.append((right_index, right_value))
                right_index += 1

        while left_index <= middle:
            merged.append((left_index, self.read(left_index)))
            left_index += 1

        while right_index <= right:
            merged.append((right_index, self.read(right_index)))
            right_index += 1

        for offset, (_, value) in enumerate(merged):
            if not self._is_running:
                return
            index = left + offset
            self.write(index, value)
            self.emit_update(index, left + offset + 1 if index < right else -1)
            if not self.sleep_and_check():
                return

    def quick_sort(self):
        self._quick_sort(0, len(self.data) - 1)

    def _quick_sort(self, low, high):
        if low >= high or not self._is_running:
            return

        pivot_index = self._partition(low, high)
        if pivot_index == -1:
            return
        self._quick_sort(low, pivot_index - 1)
        self._quick_sort(pivot_index + 1, high)

    def _partition(self, low, high):
        pivot = self.read(high)
        smaller_index = low

        for current_index in range(low, high):
            if not self._is_running:
                return -1

            current = self.read(current_index)
            self.emit_update(current_index, high)
            if not self.sleep_and_check():
                return -1

            if current < pivot:
                if smaller_index != current_index:
                    smaller = self.read(smaller_index)
                    self.write(smaller_index, current)
                    self.write(current_index, smaller)
                    self.emit_update(smaller_index, current_index)
                smaller_index += 1

        if smaller_index != high:
            smaller = self.read(smaller_index)
            self.write(smaller_index, pivot)
            self.write(high, smaller)
        self.emit_update(smaller_index, high)
        return smaller_index

    def radix_sort(self):
        if not self.data:
            return

        maximum = max(self.data)
        exponent = 1

        while maximum // exponent > 0:
            buckets = [[] for _ in range(10)]
            for index in range(len(self.data)):
                if not self._is_running:
                    return

                value = self.read(index)
                digit = (value // exponent) % 10
                buckets[digit].append(value)

            output = [value for bucket in buckets for value in bucket]
            for index, value in enumerate(output):
                if not self._is_running:
                    return
                self.write(index, value)
                self.emit_update(index, index + 1 if index + 1 < len(output) else -1)
                if not self.sleep_and_check():
                    return

            exponent *= 10


class VisualizerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []
        self.active_1 = -1
        self.active_2 = -1
        self.reads = 0
        self.writes = 0
        self.setMinimumSize(600, 400)

    def update_data(self, data, active_1=-1, active_2=-1, reads=0, writes=0):
        self.data = data.copy()
        self.active_1 = active_1
        self.active_2 = active_2
        self.reads = reads
        self.writes = writes
        self.update()  # Triggers paintEvent

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        width = self.width()
        height = self.height()

        bar_width = width / len(self.data)
        max_val = max(self.data) if self.data else 1

        for i, val in enumerate(self.data):
            # Calculate height proportional to the widget size
            bar_height = (val / max_val) * (height - 20)
            x = i * bar_width
            y = height - bar_height

            # Color coding for active comparisons
            if i == self.active_1 or i == self.active_2:
                painter.setBrush(QColor(231, 76, 60))  # Red for comparing
            else:
                painter.setBrush(QColor(41, 128, 185))  # Blue for default

            painter.setPen(Qt.NoPen)
            painter.drawRect(int(x), int(y), int(bar_width) - 1, int(bar_height))

        painter.setPen(QColor(30, 30, 30))
        painter.drawText(10, 20, f"Reads: {self.reads}   Writes: {self.writes}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Sorting Visualizer")
        
        self.num_elements = 50
        self.delay = 0.05
        self.data = []
        self.worker = None

        # Main layouts
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Canvas for drawing the bars
        self.visualizer = VisualizerWidget()
        layout.addWidget(self.visualizer)

        # Control Panel layout
        controls_layout = QHBoxLayout()
        
        # Dropdown for algorithms
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(ALGORITHMS.keys())
        controls_layout.addWidget(self.algo_combo)

        # Generate Data Button
        self.gen_btn = QPushButton("Generate New Array")
        self.gen_btn.clicked.connect(self.generate_data)
        controls_layout.addWidget(self.gen_btn)

        controls_layout.addWidget(QLabel("Array size:"))
        self.size_box = QSpinBox()
        self.size_box.setRange(2, 500)
        self.size_box.setValue(self.num_elements)
        self.size_box.setToolTip("Number of values in the new array")
        controls_layout.addWidget(self.size_box)

        # Start Button
        self.start_btn = QPushButton("Start Sorting")
        self.start_btn.clicked.connect(self.start_sorting)
        controls_layout.addWidget(self.start_btn)

        # Speed Slider
        controls_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(50)
        self.speed_slider.valueChanged.connect(self.update_speed)
        controls_layout.addWidget(self.speed_slider)
        
        layout.addLayout(controls_layout)
        
        # Initialize canvas with data
        self.update_speed()
        self.generate_data()

    def generate_data(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        self.num_elements = self.size_box.value()
        self.data = [random.randint(10, 500) for _ in range(self.num_elements)]
        self.visualizer.update_data(self.data)
        self.start_btn.setEnabled(True)

    def update_speed(self):
        # Maps slider 1-100 to a sensible delay fraction
        # High slider value = low delay (faster)
        slider_val = self.speed_slider.value()
        self.delay = (101 - slider_val) * 0.002
        if self.worker:
            self.worker.delay = self.delay

    def start_sorting(self):
        self.start_btn.setEnabled(False)
        self.gen_btn.setEnabled(False)
        self.algo_combo.setEnabled(False)

        algo = self.algo_combo.currentText()
        
        # Set up background execution thread
        self.worker = SortWorker(self.data, algo, self.delay)
        self.worker.update_signal.connect(self.visualizer.update_data)
        self.worker.finished_signal.connect(self.sorting_finished)
        self.worker.start()

    @Slot()
    def sorting_finished(self):
        self.visualizer.update_data(
            self.worker.data,
            reads=self.worker.reads,
            writes=self.worker.writes,
        )
        self.gen_btn.setEnabled(True)
        self.algo_combo.setEnabled(True)

    def closeEvent(self, event):
        # Ensure thread stops safely if user exits the application mid-sort
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())