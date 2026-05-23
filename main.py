"""
RWMod Repacker - Android App
Uses Kivy for file selection, progress bar, and repack button.
"""

import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.filechooser import FileChooserIconView
from kivy.clock import Clock
from kivy.utils import platform
from repacker_core import pack_as_rwmod

class RWRepackerApp(App):
    def build(self):
        self.title = "RWMod Repacker"
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Folder selection
        self.folder_label = Label(text="Select Mod Folder", size_hint=(1, 0.1))
        layout.add_widget(self.folder_label)

        # FileChooser (Android: needs permission, but works)
        self.file_chooser = FileChooserIconView(path='/storage/emulated/0' if platform == 'android' else '.',
                                                size_hint=(1, 0.6))
        self.file_chooser.bind(selection=self.on_selection)
        layout.add_widget(self.file_chooser)

        # Output path (simplified: same folder + .rwmod)
        self.output_label = Label(text="Output: (same folder, .rwmod)", size_hint=(1, 0.05))
        layout.add_widget(self.output_label)

        # Progress bar
        self.progress = ProgressBar(max=100, value=0, size_hint=(1, 0.05))
        layout.add_widget(self.progress)

        # Status label
        self.status_label = Label(text="Ready", size_hint=(1, 0.1))
        layout.add_widget(self.status_label)

        # Repack button
        self.repack_btn = Button(text="Repack Mod", size_hint=(1, 0.1))
        self.repack_btn.bind(on_press=self.start_repack)
        layout.add_widget(self.repack_btn)

        self.selected_folder = None
        return layout

    def on_selection(self, instance, selection):
        if selection:
            self.selected_folder = selection[0]
            self.folder_label.text = f"Selected: {os.path.basename(self.selected_folder)}"
        else:
            self.selected_folder = None
            self.folder_label.text = "Select Mod Folder"

    def start_repack(self, instance):
        if not self.selected_folder or not os.path.isdir(self.selected_folder):
            self.status_label.text = "Error: Select a valid folder"
            return

        self.repack_btn.disabled = True
        self.progress.value = 0
        self.status_label.text = "Repacking... (this may take a while)"
        threading.Thread(target=self.repack_thread, daemon=True).start()

    def repack_thread(self):
        folder = self.selected_folder
        out_path = folder + ".rwmod"

        def update_progress(value):
            Clock.schedule_once(lambda dt: setattr(self.progress, 'value', value * 100))
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"Progress: {int(value*100)}%"))

        try:
            pack_as_rwmod(folder, out_path, progress_callback=update_progress)
            Clock.schedule_once(lambda dt: self.repack_finished(True, out_path))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.repack_finished(False, str(e)))

    def repack_finished(self, success, message):
        self.repack_btn.disabled = False
        if success:
            self.status_label.text = f"Success! Saved as {os.path.basename(message)}"
            self.progress.value = 100
        else:
            self.status_label.text = f"Error: {message}"
            self.progress.value = 0

if __name__ == "__main__":
    RWRepackerApp().run()