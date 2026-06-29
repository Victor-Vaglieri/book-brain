from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QCheckBox
from PyQt6.QtCore import pyqtSignal

class ChatWidget(QWidget):
    send_message_signal = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        chat_layout = QVBoxLayout(self)
        
        top_chat_layout = QHBoxLayout()
        self.chk_local_filter = QCheckBox("Restringir busca ao documento atual")
        self.chk_local_filter.setChecked(True)
        top_chat_layout.addWidget(self.chk_local_filter)
        chat_layout.addLayout(top_chat_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        self.append_system_msg("Chatbot inicializado e pronto para interação.")
        chat_layout.addWidget(self.chat_display)
        
        self.status_log = QLabel("Status: Ocioso.")
        self.status_log.setObjectName("statusLog")
        chat_layout.addWidget(self.status_log)
        
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setPlaceholderText("Insira a consulta...")
        self.chat_input.returnPressed.connect(self.on_send_clicked)
        
        self.btn_send = QPushButton("Enviar")
        self.btn_send.setObjectName("btnSend")
        self.btn_send.clicked.connect(self.on_send_clicked)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.btn_send)
        chat_layout.addLayout(input_layout)

    def on_send_clicked(self):
        user_text = self.chat_input.text().strip()
        if not user_text:
            return
            
        self.append_user_msg(user_text)
        self.chat_input.clear()
        
        self.chat_input.setEnabled(False)
        self.btn_send.setEnabled(False)
        
        self.send_message_signal.emit(user_text, self.chk_local_filter.isChecked())

    def append_system_msg(self, text: str):
        html = f"<div align='left' style='color: white; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px; margin-right: 30px;'><b>Sistema:</b><br>{text}</div>"
        self.chat_display.append(html)

    def append_user_msg(self, text: str):
        html = f"<div align='right' style='color: white; margin-bottom: 10px; background-color: #007ACC; padding: 10px; border-radius: 8px; margin-left: 30px;'><b>Usuário:</b><br>{text}</div>"
        self.chat_display.append(html)

    def append_ai_msg(self, origin: str, text: str):
        html_text = text.replace("\n", "<br>")
        html = f"<div align='left' style='color: white; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px; margin-right: 30px;'><b>🤖 Llama 3.2 ({origin}):</b><br>{html_text}</div>"
        self.chat_display.append(html)
        self._enable_input()

    def append_error_msg(self, text: str):
        html = f"<div align='left' style='color: #ff4d4d; margin-bottom: 10px; background-color: #2b2b2b; padding: 10px; border-radius: 8px;'><b>Erro:</b><br>{text}</div>"
        self.chat_display.append(html)
        self._enable_input()

    def _enable_input(self):
        self.chat_input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.chat_input.setFocus()
        
    def set_status(self, msg: str):
        self.status_log.setText(f"Status: {msg}")
