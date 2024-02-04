import sys
from pynvml import *
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QLabel
import threading
from ctypes import c_uint, byref

class MetricUpdaterThread(QThread):
    metrics_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stopped = threading.Event()

    def run(self):
        while not self.stopped.is_set():
            self.metrics_updated.emit()
            self.stopped.wait(0.5)

    def stop(self):
        self.stopped.set()

class VideoInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video Card Information")
        self.setGeometry(100, 100, 320, 940)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        pynvml_layout = QVBoxLayout()

        self.pynvml_info_text = QTextEdit()

        pynvml_label = QLabel("PyNVML info:")

        pynvml_layout.addWidget(pynvml_label)
        pynvml_layout.addWidget(self.pynvml_info_text)

        main_layout.addLayout(pynvml_layout)

        self.metric_updater_thread = MetricUpdaterThread()
        self.metric_updater_thread.metrics_updated.connect(self.update_metrics)
        self.metric_updater_thread.start()

    def update_metrics(self):
        self.get_pynvml_info()
        self.append_pynvml_additional_info()

    def closeEvent(self, event):
        self.metric_updater_thread.stop()
        self.metric_updater_thread.wait()
        nvmlShutdown()
        event.accept()

    def get_pynvml_info(self):        
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)
        graphics_clock = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS)
        sm_clock = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_SM)
        mem_clock = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM)
        max_graphics_clock = nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_GRAPHICS)
        max_sm_clock = nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_SM)
        max_mem_clock = nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_MEM)
        temperature = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        power_usage = nvmlDeviceGetPowerUsage(handle) / 1000.0
        power_limit = nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
        perf_state = nvmlDeviceGetPerformanceState(handle)
        
        # Utilization rates
        utilization = nvmlDeviceGetUtilizationRates(handle)
        memory_utilization = utilization.memory  # Frame Buffer utilization
        gpu_utilization = utilization.gpu  # GPU Core utilization
        
        # Encoder and Decoder utilization
        encoder_util, _ = nvmlDeviceGetEncoderUtilization(handle)
        decoder_util, _ = nvmlDeviceGetDecoderUtilization(handle)

        info = (f"GPU Name: {nvmlDeviceGetName(handle)}\n"
                f"Driver Version: {nvmlSystemGetDriverVersion()}\n\n"
                f"Memory Total: {nvmlDeviceGetMemoryInfo(handle).total} bytes\n"
                f"Memory Used: {nvmlDeviceGetMemoryInfo(handle).used} bytes\n"
                f"Memory Free: {nvmlDeviceGetMemoryInfo(handle).free} bytes\n"
                f"Memory Utilization: {memory_utilization}%\n\n"
                f"GPU Utilization: {gpu_utilization}%\n\n"
                f"Encoder Utilization: {encoder_util}%\n"
                f"Decoder Utilization: {decoder_util}%\n\n"
                f"Current Graphics Clock: {graphics_clock} MHz\n"
                f"Max Graphics Clock: {max_graphics_clock} MHz\n"
                f"Current SM Clock: {sm_clock} MHz\n"
                f"Max SM Clock: {max_sm_clock} MHz\n\n"
                f"Current Memory Clock: {mem_clock} MHz\n"
                f"Max Memory Clock: {max_mem_clock} MHz\n\n"
                f"Power Usage: {power_usage}W\n"
                f"Power Limit: {power_limit}W\n\n"
                f"GPU Temperature: {temperature}°C\n\n"
                f"Current Performance State: {perf_state}")
        
        self.pynvml_info_text.setPlainText(info)
        nvmlShutdown()

    def append_pynvml_additional_info(self):
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)
        pstates_info = self.get_available_pstates(handle)

        current_text = self.pynvml_info_text.toPlainText()
        updated_text = f"{current_text}\n\nAvailable Performance States:\n\n{pstates_info}"
        self.pynvml_info_text.setPlainText(updated_text)
        nvmlShutdown()

    def get_available_pstates(self, handle):
        available_pstates = ""
        clock_types = [NVML_CLOCK_GRAPHICS, NVML_CLOCK_SM, NVML_CLOCK_MEM]
        clock_names = ["Graphics", "SM", "Memory"]

        for pstate in range(16):
            state_info = f"P-state {pstate}:\n"
            state_has_info = False

            for clock_type, clock_name in zip(clock_types, clock_names):
                try:
                    minClockMHz = c_uint()
                    maxClockMHz = c_uint()
                    nvmlDeviceGetMinMaxClockOfPState(handle, clock_type, pstate, byref(minClockMHz), byref(maxClockMHz))
                    state_info += f"  {clock_name} Clock: Min {minClockMHz.value} MHz, Max {maxClockMHz.value} MHz\n"
                    state_has_info = True
                except NVMLError:
                    pass

            if state_has_info:
                available_pstates += state_info + "\n"

        return available_pstates.strip()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = VideoInfoApp()
    window.show()
    sys.exit(app.exec())
