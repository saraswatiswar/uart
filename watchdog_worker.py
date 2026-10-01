import time
import serial
from PySide6.QtCore import QThread, Signal

class WatchdogWorker(QThread):
    connection_lost = Signal(str)
    heartbeat_received = Signal(int)

    def __init__(self, port="COM1", baudrate=115200, simulate=True, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.simulate = simulate  # Set True to bypass hardware for UI testing
        self._is_running = True
        self.current_state = 0x00
        self.seq_id = 0
        self.last_ack_time = time.time()
        self.timeout_threshold = 0.600

    def set_system_state(self, state_code: int):
        self.current_state = state_code

    def stop(self):
        self._is_running = False

    def run(self):
        if self.simulate:
            # Simulation loop for Windows UI testing without hardware
            while self._is_running:
                self.seq_id = (self.seq_id + 1) & 0xFF
                self.heartbeat_received.emit(self.seq_id)
                time.sleep(0.200)
            return

        # Real hardware serial loop (for Raspberry Pi / STM32)
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
        except serial.SerialException as e:
            self.connection_lost.emit(f"Serial port failed to open: {str(e)}")
            return

        self.last_ack_time = time.time()

        while self._is_running:
            loop_start = time.time()
            self.seq_id = (self.seq_id + 1) & 0xFF
            frame = bytearray([0xAA, 0x55, 0x01, self.seq_id, self.current_state])
            checksum = sum(frame) & 0xFF
            frame.append(checksum)
            
            try:
                ser.write(frame)
            except serial.SerialException as e:
                self.connection_lost.emit(f"Serial Write Error: {str(e)}")
                break

            if ser.in_waiting >= 6:
                rx_data = ser.read(6)
                if self._validate_ack(rx_data):
                    self.last_ack_time = time.time()
                    self.heartbeat_received.emit(rx_data[3])

            if (time.time() - self.last_ack_time) > self.timeout_threshold:
                self.connection_lost.emit("Watchdog Timeout: STM32 heartbeat ACK missing for >600ms")
                break

            elapsed = time.time() - loop_start
            time.sleep(max(0.01, 0.200 - elapsed))

        ser.close()

    def _validate_ack(self, data: bytes) -> bool:
        if len(data) < 6 or data[0] != 0xAA or data[1] != 0x55:
            return False
        return (sum(data[:5]) & 0xFF) == data[5]