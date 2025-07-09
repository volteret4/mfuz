# submodules/muspy/ics_manager.py
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QDialog, QVBoxLayout,
                           QHBoxLayout, QLabel, QSpinBox, QPushButton,
                           QCheckBox, QDialogButtonBox, QComboBox)

try:
    from icalendar import Calendar, Event
    ICS_AVAILABLE = True
except ImportError:
    ICS_AVAILABLE = False

class ICSManager:
    def __init__(self, parent, project_root):
        self.parent = parent
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)

        if not ICS_AVAILABLE:
            self.logger.warning("icalendar library not available. ICS functionality will be disabled.")

    def is_available(self):
        """Check if ICS functionality is available"""
        return ICS_AVAILABLE

    def create_ics_from_releases(self, releases, table=None):
        """
        Create an ICS calendar file from selected releases

        Args:
            releases (list): List of release dictionaries
            table (QTableWidget, optional): Table widget to get selection from
        """
        if not self.is_available():
            QMessageBox.warning(
                self.parent,
                "Funcionalidad no disponible",
                "La librería 'icalendar' no está instalada. Instálala con:\npip install icalendar"
            )
            return

        if not releases:
            QMessageBox.warning(self.parent, "Sin lanzamientos", "No hay lanzamientos para exportar.")
            return

        # Get user preferences for the calendar
        preferences = self.show_ics_preferences_dialog(len(releases))
        if not preferences:
            return  # User cancelled

        try:
            # Create calendar
            cal = Calendar()
            cal.add('prodid', '-//Muspy Release Tracker//mxm.dk//')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')
            cal.add('x-wr-calname', 'Próximos Lanzamientos Musicales')
            cal.add('x-wr-caldesc', 'Lanzamientos de álbumes y EPs de tus artistas favoritos')

            events_created = 0

            for release in releases:
                try:
                    # Parse release date
                    release_date_str = release.get('date', '')
                    if not release_date_str or release_date_str == 'No date':
                        continue

                    release_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()

                    # Create event
                    event = Event()

                    # Basic event info
                    artist_name = release.get('artist', {}).get('name', 'Unknown Artist')
                    release_title = release.get('title', 'Unknown Release')
                    release_type = release.get('type', 'Album')

                    # Event title
                    event.add('summary', f"🎵 {artist_name} - {release_title}")

                    # Event description
                    description_parts = [
                        f"Nuevo {release_type.lower()} de {artist_name}",
                        f"Título: {release_title}",
                        f"Tipo: {release_type}"
                    ]

                    # Add additional details if available
                    if release.get('format'):
                        description_parts.append(f"Formato: {release.get('format')}")
                    if release.get('tracks'):
                        description_parts.append(f"Pistas: {release.get('tracks')}")
                    if release.get('country'):
                        description_parts.append(f"País: {release.get('country')}")

                    # Add URLs if available
                    if release.get('mbid'):
                        description_parts.append(f"MusicBrainz: https://musicbrainz.org/release/{release.get('mbid')}")

                    event.add('description', '\n'.join(description_parts))

                    # Date and time settings
                    if preferences['all_day']:
                        event.add('dtstart', release_date)
                        event.add('dtend', release_date + timedelta(days=1))
                    else:
                        # Set specific time
                        event_datetime = datetime.combine(release_date, preferences['event_time'])
                        event.add('dtstart', event_datetime)
                        event.add('dtend', event_datetime + timedelta(hours=1))

                    # Additional properties
                    event.add('uid', f"muspy-release-{release.get('mbid', events_created)}@muspy.local")
                    event.add('dtstamp', datetime.now())
                    event.add('created', datetime.now())
                    event.add('last-modified', datetime.now())

                    # Categories
                    event.add('categories', ['MUSIC', 'RELEASE', release_type.upper()])

                    # Set priority based on release type
                    priority_map = {
                        'Album': 5,
                        'EP': 7,
                        'Single': 9
                    }
                    event.add('priority', priority_map.get(release_type, 5))

                    # Add reminder if requested
                    if preferences['add_reminder']:
                        from icalendar import Alarm
                        alarm = Alarm()
                        alarm.add('action', 'DISPLAY')
                        alarm.add('description', f"Recordatorio: {artist_name} - {release_title}")
                        alarm.add('trigger', timedelta(days=-preferences['reminder_days']))
                        event.add_component(alarm)

                    cal.add_component(event)
                    events_created += 1

                except Exception as e:
                    self.logger.error(f"Error creating event for release {release}: {e}")
                    continue

            if events_created == 0:
                QMessageBox.warning(self.parent, "Sin eventos", "No se pudieron crear eventos válidos.")
                return

            # Save calendar to file
            self.save_calendar_to_file(cal, events_created)

        except Exception as e:
            self.logger.error(f"Error creating ICS calendar: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Error al crear el archivo ICS: {str(e)}"
            )

    def show_ics_preferences_dialog(self, num_releases):
        """
        Show dialog to configure ICS export preferences

        Args:
            num_releases (int): Number of releases to export

        Returns:
            dict or None: Preferences dictionary or None if cancelled
        """
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Configurar Exportación ICS")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Info label
        info_label = QLabel(f"Configurar la exportación de {num_releases} lanzamientos a calendario ICS")
        layout.addWidget(info_label)

        # All-day events checkbox
        all_day_check = QCheckBox("Eventos de día completo")
        all_day_check.setChecked(True)
        layout.addWidget(all_day_check)

        # Time selection (disabled if all-day is checked)
        time_layout = QHBoxLayout()
        time_label = QLabel("Hora del evento:")
        time_combo = QComboBox()

        # Populate time options
        for hour in range(24):
            time_combo.addItem(f"{hour:02d}:00", hour)
        time_combo.setCurrentIndex(12)  # Default to 12:00
        time_combo.setEnabled(False)  # Disabled by default

        time_layout.addWidget(time_label)
        time_layout.addWidget(time_combo)
        layout.addLayout(time_layout)

        # Connect all-day checkbox to enable/disable time selection
        def toggle_time_selection(checked):
            time_combo.setEnabled(not checked)
            time_label.setEnabled(not checked)

        all_day_check.toggled.connect(toggle_time_selection)

        # Reminder options
        reminder_check = QCheckBox("Añadir recordatorio")
        reminder_check.setChecked(True)
        layout.addWidget(reminder_check)

        reminder_layout = QHBoxLayout()
        reminder_label = QLabel("Días antes:")
        reminder_spin = QSpinBox()
        reminder_spin.setRange(1, 30)
        reminder_spin.setValue(3)

        reminder_layout.addWidget(reminder_label)
        reminder_layout.addWidget(reminder_spin)
        layout.addLayout(reminder_layout)

        # Connect reminder checkbox
        def toggle_reminder_options(checked):
            reminder_spin.setEnabled(checked)
            reminder_label.setEnabled(checked)

        reminder_check.toggled.connect(toggle_reminder_options)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            from datetime import time
            return {
                'all_day': all_day_check.isChecked(),
                'event_time': time(time_combo.currentData(), 0) if not all_day_check.isChecked() else None,
                'add_reminder': reminder_check.isChecked(),
                'reminder_days': reminder_spin.value()
            }

        return None

    def save_calendar_to_file(self, calendar, events_count):
        """
        Save calendar to file with file dialog

        Args:
            calendar: icalendar Calendar object
            events_count (int): Number of events in calendar
        """
        try:
            # Suggest default filename
            default_filename = f"proximos_lanzamientos_{datetime.now().strftime('%Y%m%d')}.ics"

            # Show file dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Guardar Calendario ICS",
                default_filename,
                "Archivos ICS (*.ics);;Todos los archivos (*)"
            )

            if filename:
                # Ensure .ics extension
                if not filename.lower().endswith('.ics'):
                    filename += '.ics'

                # Write calendar to file
                with open(filename, 'wb') as f:
                    f.write(calendar.to_ical())

                # Show success message
                QMessageBox.information(
                    self.parent,
                    "Exportación Exitosa",
                    f"Calendario ICS guardado exitosamente en:\n{filename}\n\n"
                    f"Eventos creados: {events_count}\n\n"
                    f"Puedes importar este archivo en cualquier aplicación de calendario "
                    f"(Google Calendar, Outlook, Apple Calendar, etc.)"
                )

                self.logger.info(f"ICS calendar saved successfully: {filename} ({events_count} events)")

        except Exception as e:
            self.logger.error(f"Error saving ICS file: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent,
                "Error al Guardar",
                f"Error al guardar el archivo ICS:\n{str(e)}"
            )

    def create_ics_from_selected_table_rows(self, table):
        """
        Create ICS from selected rows in a table

        Args:
            table (QTableWidget): Table widget with releases
        """
        if not table:
            return

        # Get selected rows
        selected_rows = set()
        for item in table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(
                self.parent,
                "Sin selección",
                "Selecciona al menos una fila en la tabla para exportar."
            )
            return

        # Extract release data from selected rows
        selected_releases = []

        for row in selected_rows:
            try:
                # Try to get data from UserRole first
                item = table.item(row, 0)
                if item:
                    release_data = item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(release_data, dict):
                        selected_releases.append(release_data)
                        continue

                # Fallback: construct release data from table columns
                release = {}

                # Get data from table columns
                if table.item(row, 0):  # Artist
                    release['artist'] = {'name': table.item(row, 0).text()}
                if table.item(row, 1):  # Title
                    release['title'] = table.item(row, 1).text()
                if table.item(row, 2):  # Type
                    release['type'] = table.item(row, 2).text()
                if table.item(row, 3):  # Date
                    release['date'] = table.item(row, 3).text()

                # Try to get MBID from any column's UserRole data
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item:
                        data = item.data(Qt.ItemDataRole.UserRole)
                        if isinstance(data, dict) and 'mbid' in data:
                            release['mbid'] = data['mbid']
                            break
                        elif isinstance(data, str) and len(data) == 36 and data.count('-') == 4:
                            release['mbid'] = data
                            break

                if release:
                    selected_releases.append(release)

            except Exception as e:
                self.logger.error(f"Error extracting data from row {row}: {e}")
                continue

        if not selected_releases:
            QMessageBox.warning(
                self.parent,
                "Sin datos",
                "No se pudieron extraer datos válidos de las filas seleccionadas."
            )
            return

        # Create ICS from selected releases
        self.create_ics_from_releases(selected_releases, table)
