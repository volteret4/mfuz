from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QCheckBox,
    QScrollArea, QFormLayout, QPlainTextEdit
)
from PyQt6.QtCore import Qt


class GenericScriptModule:
    """Wizard step for any script: renders its config section as a dynamic form."""

    def __init__(self, parent, script_key, title=None, description="", config=None):
        self.parent = parent
        self.script_key = script_key
        self.TITLE = title or script_key.split('/')[-1].replace('_', ' ').title()
        self.DESCRIPTION = description
        self.config = config or {}
        self._form_widgets = {}   # key -> (widget, original_type)
        self._ui_initialized = False

    def setup_ui(self, container):
        if self._ui_initialized:
            return
        self._ui_initialized = True

        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)

        # Title
        title_label = QLabel(self.TITLE)
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(title_label)

        script_config = self.config.get(self.script_key, {})

        if not script_config:
            layout.addWidget(QLabel("No hay configuración disponible para este script."))
            layout.addStretch()
            return

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        form_layout.setContentsMargins(0, 0, 8, 0)
        form_layout.setVerticalSpacing(6)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        for key, value in script_config.items():
            if isinstance(value, dict):
                continue  # nested dicts skipped
            label = QLabel(key.replace('_', ' ').capitalize() + ':')
            widget = self._make_widget(value)
            self._form_widgets[key] = (widget, type(value))
            form_layout.addRow(label, widget)

    def _make_widget(self, value):
        if isinstance(value, bool):
            w = QCheckBox()
            w.setChecked(value)
            return w
        if isinstance(value, list):
            w = QPlainTextEdit()
            w.setPlainText('\n'.join(str(v) for v in value))
            w.setMaximumHeight(72)
            return w
        w = QLineEdit()
        w.setText('' if value is None else str(value))
        return w

    def validate(self):
        return True

    def update_config_from_ui(self):
        if not hasattr(self.parent, 'config_data'):
            return {}

        script_config = self.parent.config_data.get(self.script_key, {})
        for key, (widget, orig_type) in self._form_widgets.items():
            if isinstance(widget, QCheckBox):
                script_config[key] = widget.isChecked()
            elif isinstance(widget, QPlainTextEdit):
                lines = [l for l in widget.toPlainText().splitlines() if l.strip()]
                script_config[key] = lines
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if orig_type is int:
                    try:
                        script_config[key] = int(text)
                    except ValueError:
                        script_config[key] = text
                elif orig_type is float:
                    try:
                        script_config[key] = float(text)
                    except ValueError:
                        script_config[key] = text
                else:
                    script_config[key] = text if text else None

        self.parent.config_data[self.script_key] = script_config
        return self.parent.config_data
