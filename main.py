import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Slot, Qt
from watchdog_worker import WatchdogWorker

class MTA_MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MTA Control Interface - Safety Watchdog Active")
        self.resize(500, 300)

        self.ablation_active = False

        # UI Setup
        self.status_label = QLabel("System State: IDLE")
        self.wd_label = QLabel("Watchdog: Initializing...")
        self.btn_toggle = QPushButton("Start Ablation")
        self.btn_toggle.clicked.connect(self.toggle_ablation)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.wd_label)
        layout.addWidget(self.btn_toggle)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Initialize Watchdog Thread with simulate=True for Windows GUI testing
        self.wd_thread = WatchdogWorker(simulate=True)
        self.wd_thread.connection_lost.connect(self.handle_watchdog_failure)
        self.wd_thread.heartbeat_received.connect(self.update_wd_indicator)
        self.wd_thread.start()

    @Slot(int)
    def update_wd_indicator(self, seq_id):
        self.wd_label.setText(f"Watchdog: OK (ACK Seq: {seq_id})")

    @Slot(str)
    def handle_watchdog_failure(self, error_msg):
        """IEC 62304 Safe State Handler: Instantly stop treatment and warn user."""
        self.ablation_active = False
        self.status_label.setText(f"CRITICAL FAULT: {error_msg}")
        self.status_label.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.btn_toggle.setEnabled(False)
        
        # Log error to console/file
        print(f"[ALARM LOGGED]: {error_msg}")

    def toggle_ablation(self):
        if not self.ablation_active:
            self.ablation_active = True
            self.status_label.setText("System State: ABLATION ACTIVE")
            self.btn_toggle.setText("Stop Ablation")
            self.wd_thread.set_system_state(0x02)  # Notify thread of ACTIVE state
        else:
            self.ablation_active = False
            self.status_label.setText("System State: IDLE")
            self.btn_toggle.setText("Start Ablation")
            self.wd_thread.set_system_state(0x00)  # Notify thread of IDLE state

    def closeEvent(self, event):
        self.wd_thread.stop()
        self.wd_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MTA_MainWindow()
    window.show()
    sys.exit(app.exec())