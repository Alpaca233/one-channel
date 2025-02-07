#!/usr/bin/env python3
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from datetime import datetime
import sys
import csv
from controller import TCMController as TCMController
import warnings
warnings.filterwarnings("ignore")

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class TemperatureUpdateSignal(QObject):
    update = pyqtSignal(float)

class TemperatureGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Temperature Controller')
        self.setGeometry(100, 100, 800, 600)

        # Initialize controller
        self.controller = TCMController("FTDI9EWB")

        # Setup data
        self.temps = []
        self.times = []
        self.targets = []

        # Setup intervals and windows
        self.query_interval = 2
        self.window_size = 60
        self.last_update = 0

        # Create update signal to handle thread safety
        self.update_signal = TemperatureUpdateSignal()
        self.update_signal.update.connect(self.handle_temperature_update)

        # Set the temperature callback to emit signal
        self.controller.temperature_updating_callback = self.temperature_callback

        # Setup UI
        self.init_ui()
        self.temp_input.setText(f"{self.controller.target_temperature:.2f}")

        self.controller.actual_temp_updating_thread.start()

    def create_plot_controls(self):
        control_widget = QWidget()
        layout = QHBoxLayout(control_widget)

        # Query interval control
        layout.addWidget(QLabel("Query Interval:"))
        interval_input = QSpinBox()
        interval_input.setMinimum(2)
        interval_input.setValue(2)
        interval_input.setSuffix(" s")
        layout.addWidget(interval_input)

        # Window size control
        layout.addWidget(QLabel("Window Size:"))
        window_input = QSpinBox()
        window_input.setMinimum(10)
        window_input.setMaximum(3600)  # 1 hour maximum
        window_input.setValue(60)
        window_input.setSuffix(" s")
        layout.addWidget(window_input)

        # Connect signals
        interval_input.valueChanged.connect(self.set_interval)
        window_input.valueChanged.connect(self.set_window)
        self.interval_input = interval_input
        self.window_input = window_input

        return control_widget

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Create temperature controls
        temp_controls = QGroupBox("Temperature Control")
        temp_controls_layout = QVBoxLayout()

        temp_layout = QHBoxLayout()
        self.temp_label = QLabel("0.0°C")
        self.temp_input = QLineEdit()
        self.set_btn = QPushButton("Set")
        self.save_btn = QPushButton("Save")
        temp_layout.addWidget(QLabel("Current:"))
        temp_layout.addWidget(self.temp_label)
        temp_layout.addWidget(QLabel("Target:"))
        temp_layout.addWidget(self.temp_input)
        temp_layout.addWidget(QLabel("°C"))
        temp_layout.addWidget(self.set_btn)
        temp_layout.addWidget(self.save_btn)

        temp_controls_layout.addLayout(temp_layout)
        temp_controls.setLayout(temp_controls_layout)

        # Add controls to main layout
        main_layout.addWidget(temp_controls)

        # Create plot section
        plot_group = QGroupBox("Temperature Plot")
        plot_layout = QVBoxLayout()

        # Add plot controls
        plot_layout.addWidget(self.create_plot_controls())

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.record_btn = QPushButton("Start Recording")

        plot_layout.addWidget(self.canvas)
        plot_layout.addWidget(self.record_btn)
        plot_group.setLayout(plot_layout)

        # Add plot section to main layout
        main_layout.addWidget(plot_group)

        # Connect signals
        self.set_btn.clicked.connect(self.set_temp)
        self.save_btn.clicked.connect(self.save_temp)
        self.record_btn.clicked.connect(self.toggle_record)

    def set_interval(self, value):
        self.query_interval = value

    def set_window(self, value):
        self.window_size = value
        self._update_plot()

    def handle_temperature_update(self, temp):
        current_time = datetime.now().timestamp()

        if current_time - self.last_update >= self.query_interval:
            self.temp_label.setText(f"{temp:.1f}°C")
            self.temps.append(temp)
            self.targets.append(self.controller.target_temperature)
            self.times.append(current_time)

            # Write to CSV if recording
            if hasattr(self, 'writer') and self.record_btn.text() == "Stop Recording":
                self.writer.writerow([datetime.fromtimestamp(current_time), temp, self.controller.target_temperature])

            self._update_plot()
            self.last_update = current_time

        # Cleanup old data
        while self.times and current_time - self.times[0] > self.window_size:
            self.times.pop(0)
            self.temps.pop(0)
            self.targets.pop(0)

    def _update_plot(self):
        if not self.temps or not self.times:
            return

        self.canvas.axes.clear()

        # Plot the data
        self.canvas.axes.plot(self.times, self.temps, 'b-', label='Actual')
        self.canvas.axes.plot(self.times, self.targets, 'r--', label='Target')

        # Set y-axis limits with padding
        y_min = min(min(self.temps), min(self.targets))
        y_max = max(max(self.temps), max(self.targets))
        padding = (y_max - y_min) * 0.1 if y_max != y_min else 1.0
        self.canvas.axes.set_ylim([y_min - padding, y_max + padding])

        # Set x-axis to show window size
        current_time = self.times[-1]
        self.canvas.axes.set_xlim([current_time - self.window_size, current_time])

        # Format time axis
        self.canvas.axes.set_xlabel('Seconds Ago')
        self.canvas.axes.set_ylabel('Temperature (°C)')
        self.canvas.axes.set_title('Temperature')
        self.canvas.axes.grid(True)
        self.canvas.axes.legend()

        # Convert timestamps to relative time for display
        self.canvas.axes.set_xticklabels([f"{x:.0f}" for x in current_time - self.canvas.axes.get_xticks()])

        self.canvas.draw()

    def set_temp(self):
        try:
            temp = float(self.temp_input.text())
            self.controller.set_target_temperature(temp)
        except ValueError:
            print("Invalid temperature")

    def save_temp(self):
        self.controller.save_target_temperature()

    def toggle_record(self):
        if self.record_btn.text() == "Start Recording":
            self.record_btn.setText("Stop Recording")
            filename = f"temperature_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.file = open(filename, 'w', newline='')
            self.writer = csv.writer(self.file)
            self.writer.writerow(['Time', 'Actual Temperature', 'Target Temperature'])
        else:
            self.record_btn.setText("Start Recording")
            self.file.close()

    def temperature_callback(self, temp1, _):
        # This runs in the controller thread, emit signal to handle in GUI thread
        self.update_signal.update.emit(temp1)

    def closeEvent(self, event):
        # Stop the controller's update thread
        self.controller.terminate_temperature_updating_thread = True
        self.controller.actual_temp_updating_thread.join()
        
        # Close any open files
        if hasattr(self, 'file') and self.file:
            self.file.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TemperatureGUI()
    window.show()
    sys.exit(app.exec_())
