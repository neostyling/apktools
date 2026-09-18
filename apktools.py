"""apktools - envoie un APK compile vers le telephone via adb."""

import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import adb_bridge as adb
import config

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

COLOR_NEUTRAL = None
COLOR_SUCCESS = ("#2FA572", "#3FCB88")
COLOR_ERROR = ("#D64545", "#E86868")
COLOR_MUTED = ("gray40", "gray60")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("apktools")
        self.resizable(False, False)

        self.cfg = config.load_config()
        self.adb_path = adb.find_adb()
        self.devices: list[tuple[str, str]] = []
        self.selected_serial = tk.StringVar()
        self.selected_apk = tk.StringVar()
        self.apk_list_frame: ctk.CTkFrame | None = None

        self._build_ui()
        self._load_projects()
        self._refresh_devices()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            self,
            text="apktools",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        header.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 0))
        subtitle = ctk.CTkLabel(
            self,
            text="Envoyer un build Flutter vers le telephone",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_MUTED,
        )
        subtitle.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))

        # --- carte projet ---
        project_card = ctk.CTkFrame(self, corner_radius=12)
        project_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        project_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(project_card, text="Projet", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 4)
        )
        self.project_menu = ctk.CTkOptionMenu(
            project_card,
            values=[],
            command=self._on_project_selected,
            width=220,
        )
        self.project_menu.grid(row=1, column=0, columnspan=1, sticky="ew", padx=(14, 8), pady=(0, 12))
        ctk.CTkButton(
            project_card, text="Refresh", width=80, fg_color="transparent", border_width=1,
            command=self._on_refresh,
        ).grid(row=1, column=1, sticky="e", padx=(0, 8), pady=(0, 12))
        ctk.CTkButton(
            project_card, text="+ Ajouter", width=90,
            command=self._on_add_project,
        ).grid(row=1, column=2, sticky="e", padx=(0, 14), pady=(0, 12))

        # --- carte APK ---
        apk_card = ctk.CTkFrame(self, corner_radius=12)
        apk_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        ctk.CTkLabel(apk_card, text="APK trouves", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=14, pady=(12, 4)
        )
        self.apk_list_frame = ctk.CTkFrame(apk_card, fg_color="transparent")
        self.apk_list_frame.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(self.apk_list_frame, text="(aucun projet selectionne)", text_color=COLOR_MUTED).pack(anchor="w")

        # --- carte appareil ---
        device_card = ctk.CTkFrame(self, corner_radius=12)
        device_card.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 16))
        device_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(device_card, text="Appareil", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 4)
        )
        self.device_label = ctk.CTkLabel(device_card, text="...", anchor="w")
        self.device_label.grid(row=1, column=0, sticky="w", padx=(14, 8), pady=(0, 12))
        self.device_menu = ctk.CTkOptionMenu(
            device_card, values=[], width=180, variable=self.selected_serial,
            command=lambda _v: self._update_send_state(),
        )
        self.device_menu.grid(row=1, column=1, sticky="e", padx=(0, 14), pady=(0, 12))
        self.device_menu.grid_remove()

        # --- envoi ---
        self.send_button = ctk.CTkButton(
            self, text="Envoyer", height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_send,
        )
        self.send_button.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 10))

        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.grid(row=6, column=0, sticky="ew", padx=20)
        self.progress.grid_remove()

        self.status_label = ctk.CTkLabel(self, text="Pret.", anchor="w", text_color=COLOR_MUTED)
        self.status_label.grid(row=7, column=0, sticky="ew", padx=20, pady=(6, 18))

        self._update_send_state()

    # ------------------------------------------------------------- projets

    def _load_projects(self):
        names = [p["name"] for p in self.cfg["projects"]]
        if not names:
            self.project_menu.configure(values=[], state="disabled")
            self.project_menu.set("(aucun projet)")
            self._set_status("Aucun projet configure. Cliquer sur + Ajouter.")
            return
        self.project_menu.configure(values=names, state="normal")
        last = self.cfg.get("last_project")
        self.project_menu.set(last if last in names else names[0])
        self._on_project_change()

    def _on_project_selected(self, _value: str):
        self._on_project_change()

    def _on_project_change(self):
        name = self.project_menu.get()
        if not name:
            return
        config.set_last_project(self.cfg, name)
        project = config.get_project(self.cfg, name)
        if project:
            self._populate_apk_list(project)

    def _on_add_project(self):
        existing_names = [p["name"] for p in self.cfg["projects"]]
        dialog = AddProjectDialog(self, existing_names)
        self.wait_window(dialog)
        if not dialog.result:
            return

        self.cfg["projects"].append(dialog.result)
        config.save_config(self.cfg)

        names = [p["name"] for p in self.cfg["projects"]]
        self.project_menu.configure(values=names, state="normal")
        self.project_menu.set(dialog.result["name"])
        self._on_project_change()

    def _populate_apk_list(self, project: dict):
        for child in self.apk_list_frame.winfo_children():
            child.destroy()
        self.selected_apk.set("")

        build_dir = Path(project["build_dir"])
        if not build_dir.is_dir():
            ctk.CTkLabel(
                self.apk_list_frame, text=f"Dossier introuvable : {build_dir}", text_color=COLOR_ERROR
            ).pack(anchor="w")
            self._set_status(f"Dossier de build introuvable : {build_dir}", "error")
            self._update_send_state()
            return

        apks = sorted(build_dir.glob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not apks:
            ctk.CTkLabel(
                self.apk_list_frame, text="Aucun APK trouve. Compiler le projet d'abord.", text_color=COLOR_MUTED
            ).pack(anchor="w")
            self._set_status("Aucun APK trouve.", "error")
            self._update_send_state()
            return

        for apk in apks:
            stat = apk.stat()
            size_mb = stat.st_size / (1024 * 1024)
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
            text = f"{apk.name}   ({size_mb:.1f} Mo, {when})"
            ctk.CTkRadioButton(
                self.apk_list_frame,
                text=text,
                value=str(apk),
                variable=self.selected_apk,
                command=self._update_send_state,
            ).pack(anchor="w", pady=3)

        self.selected_apk.set(str(apks[0]))
        self._set_status("Pret.")
        self._update_send_state()

    def _on_refresh(self):
        name = self.project_menu.get()
        if name:
            project = config.get_project(self.cfg, name)
            if project:
                self._populate_apk_list(project)
        self._refresh_devices()

    # ------------------------------------------------------------ appareil

    def _refresh_devices(self):
        if not self.adb_path:
            self.device_label.configure(text="adb.exe introuvable", text_color=COLOR_ERROR)
            self._set_status("adb.exe introuvable - verifier le PATH ou l'installation du SDK Android.", "error")
            self.devices = []
            self.device_menu.grid_remove()
            self._update_send_state()
            return

        try:
            self.devices = adb.list_devices(self.adb_path)
        except (subprocess.SubprocessError, OSError) as exc:
            self.device_label.configure(text="erreur adb", text_color=COLOR_ERROR)
            self._set_status(f"Erreur lors de l'appel a adb : {exc}", "error")
            self.devices = []
            self._update_send_state()
            return

        online = [d for d in self.devices if d[1] == "device"]

        if not self.devices:
            self.device_label.configure(text="aucun appareil detecte", text_color=COLOR_MUTED)
            self.device_menu.grid_remove()
        elif not online:
            serial, state = self.devices[0]
            state_text = {
                "unauthorized": "non autorise",
                "offline": "hors ligne",
            }.get(state, state)
            self.device_label.configure(text=f"{serial} ({state_text})", text_color=COLOR_ERROR)
            self.device_menu.grid_remove()
        elif len(online) == 1:
            serial, _ = online[0]
            self.device_label.configure(text=f"{serial} (pret)", text_color=COLOR_SUCCESS)
            self.selected_serial.set(serial)
            self.device_menu.grid_remove()
        else:
            self.device_label.configure(text="plusieurs appareils, choisir :", text_color=COLOR_SUCCESS)
            self.device_menu.configure(values=[d[0] for d in online])
            self.device_menu.grid()
            if self.selected_serial.get() not in [d[0] for d in online]:
                self.selected_serial.set(online[0][0])

        self._update_send_state()

    def _online_serial(self) -> str | None:
        online = [d for d in self.devices if d[1] == "device"]
        if not online:
            return None
        if len(online) == 1:
            return online[0][0]
        serial = self.selected_serial.get()
        return serial if serial in [d[0] for d in online] else None

    # ------------------------------------------------------------- envoi

    def _update_send_state(self):
        ready = bool(self.adb_path and self._online_serial() and self.selected_apk.get())
        self.send_button.configure(state="normal" if ready else "disabled")

    def _set_status(self, text: str, kind: str = "neutral"):
        color = {"neutral": COLOR_MUTED, "success": COLOR_SUCCESS, "error": COLOR_ERROR}[kind]
        self.status_label.configure(text=text, text_color=color)

    def _on_send(self):
        name = self.project_menu.get()
        project = config.get_project(self.cfg, name)
        apk_path = self.selected_apk.get()
        serial = self._online_serial()
        if not (project and apk_path and serial and self.adb_path):
            return

        device_dest = f"{project['device_dest']}/{Path(apk_path).name}"
        self.send_button.configure(state="disabled")
        self._set_status(f"Envoi en cours vers {device_dest} ...")
        self.progress.grid()
        self.progress.start()

        thread = threading.Thread(
            target=self._push_worker,
            args=(self.adb_path, serial, apk_path, device_dest),
            daemon=True,
        )
        thread.start()

    def _push_worker(self, adb_path: str, serial: str, apk_path: str, device_dest: str):
        try:
            result = adb.push(adb_path, serial, apk_path, device_dest)
        except subprocess.TimeoutExpired:
            self.after(0, self._push_done, False, device_dest, "Envoi expire - verifier la connexion USB.")
            return
        except (subprocess.SubprocessError, OSError) as exc:
            self.after(0, self._push_done, False, device_dest, str(exc))
            return

        if result.returncode != 0:
            self.after(0, self._push_done, False, device_dest, result.stderr.strip())
        else:
            self.after(0, self._push_done, True, device_dest, "")

    def _push_done(self, success: bool, device_dest: str, error: str):
        self.progress.stop()
        self.progress.grid_remove()
        self.send_button.configure(state="normal")
        if success:
            self._set_status(f"Envoye vers {device_dest}", "success")
        else:
            self._set_status(f"Echec de l'envoi vers {device_dest}", "error")
            messagebox.showerror("Echec de l'envoi", error or "Erreur inconnue.")
        self._update_send_state()


class AddProjectDialog(ctk.CTkToplevel):
    def __init__(self, parent: tk.Misc, existing_names: list[str]):
        super().__init__(parent)
        self.title("Ajouter un projet")
        self.resizable(False, False)
        self.result: dict | None = None
        self._existing_names = existing_names
        self._dest_auto = True

        self.grid_columnconfigure(1, weight=1)
        pad = {"padx": 14, "pady": (10, 0)}

        ctk.CTkLabel(self, text="Nom du projet").grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        self.name_var = tk.StringVar()
        name_entry = ctk.CTkEntry(self, textvariable=self.name_var, width=280)
        name_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(2, 0))
        self.name_var.trace_add("write", self._on_name_change)

        ctk.CTkLabel(self, text="Dossier de build (flutter-apk)").grid(row=2, column=0, columnspan=2, sticky="w", **pad)
        self.build_dir_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.build_dir_var, width=200).grid(
            row=3, column=0, sticky="ew", padx=(14, 8), pady=(2, 0)
        )
        ctk.CTkButton(self, text="Parcourir...", width=90, command=self._browse).grid(
            row=3, column=1, sticky="e", padx=(0, 14), pady=(2, 0)
        )

        ctk.CTkLabel(self, text="Destination sur le telephone").grid(row=4, column=0, columnspan=2, sticky="w", **pad)
        self.dest_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.dest_var, width=280).grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=(2, 0)
        )
        self.dest_var.trace_add("write", self._on_dest_edited)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, pady=16)
        ctk.CTkButton(
            btn_frame, text="Annuler", width=90, fg_color="transparent", border_width=1,
            command=self._cancel,
        ).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Ajouter", width=90, command=self._confirm).pack(side="left", padx=6)

        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        name_entry.focus_set()
        self.grab_set()

    def _on_name_change(self, *_args):
        if self._dest_auto:
            name = self.name_var.get().strip()
            self.dest_var.set(f"/sdcard/Download/{name}" if name else "")
            self._dest_auto = True  # writing dest_var above triggers _on_dest_edited; restore auto-sync

    def _on_dest_edited(self, *_args):
        # Once the user edits the destination field directly, stop auto-syncing it to the name.
        self._dest_auto = False

    def _browse(self):
        chosen = filedialog.askdirectory(title="Choisir le dossier de build (flutter-apk)", parent=self)
        if chosen:
            self.build_dir_var.set(chosen)

    def _confirm(self):
        name = self.name_var.get().strip()
        build_dir = self.build_dir_var.get().strip()
        dest = self.dest_var.get().strip()

        if not name:
            messagebox.showerror("Erreur", "Le nom du projet est requis.", parent=self)
            return
        if name in self._existing_names:
            messagebox.showerror("Erreur", f"Un projet nomme '{name}' existe deja.", parent=self)
            return
        if not build_dir:
            messagebox.showerror("Erreur", "Le dossier de build est requis.", parent=self)
            return
        if not dest:
            messagebox.showerror("Erreur", "Le dossier de destination sur le telephone est requis.", parent=self)
            return

        self.result = {"name": name, "build_dir": build_dir, "device_dest": dest}
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
