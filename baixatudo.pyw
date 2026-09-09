from __future__ import annotations

import os
import hashlib
import tempfile
import zipfile
import queue
import shutil
import subprocess
import sys
import threading
import traceback
import urllib.request
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse
import tkinter as tk
import tkinter.font as tkfont


IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
APP_DATA_ROOT = Path(os.environ.get("LOCALAPPDATA", APP_ROOT)) / "Baixatudo" if os.name == "nt" else Path.home() / ".baixatudo"
TOOLS_DIR = APP_DATA_ROOT / "tools" if IS_FROZEN else APP_ROOT / "tools"
YTDLP_LOCAL = TOOLS_DIR / "yt-dlp.exe"
BUNDLED_YTDLP = BUNDLE_ROOT / "tools" / "yt-dlp.exe"
YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

QUALITY_OPTIONS = (
    "MP4 compativel",
    "MP4 ate 1080p",
    "Melhor qualidade",
    "Somente audio MP3",
)

FFMPEG_QUALITY_OPTIONS = {
    "MP4 ate 1080p",
    "Melhor qualidade",
    "Somente audio MP3",
}


def default_download_folder() -> Path:
    return Path.home() / "Downloads" / "Baixatudo"


def find_yt_dlp() -> str | None:
    if YTDLP_LOCAL.exists():
        return str(YTDLP_LOCAL)

    if BUNDLED_YTDLP.exists():
        return str(BUNDLED_YTDLP)

    for name in ("yt-dlp.exe", "yt-dlp"):
        found = shutil.which(name)
        if found:
            return found

    return None


def find_ffmpeg() -> str | None:
    # yt-dlp needs both programs in the directory passed to --ffmpeg-location.
    directories = []
    for root in (TOOLS_DIR, APP_ROOT / "tools", BUNDLE_ROOT / "tools"):
        directories.extend((root, root / "ffmpeg" / "bin"))
    for name in ("ffmpeg.exe", "ffmpeg"):
        found = shutil.which(name)
        if found:
            directories.append(Path(found).parent)
    for directory in directories:
        for suffix in (".exe", ""):
            if all((directory / (name + suffix)).is_file() for name in ("ffmpeg", "ffprobe")):
                return str(directory)
    return None


def ensure_ffmpeg(report, stop_event=None) -> str:
    location = find_ffmpeg()
    if location:
        return location
    if os.name != "nt":
        raise RuntimeError("Instale ffmpeg e ffprobe no PATH para converter ou mesclar arquivos.")

    def check_cancelled():
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("Instalacao do FFmpeg interrompida.")

    report("log", "Instalando FFmpeg e ffprobe de gyan.dev. Aguarde o download das ferramentas.")
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ffmpeg-", dir=TOOLS_DIR) as temporary:
        staging = Path(temporary)
        archive_path = staging / "ffmpeg.zip"
        request = urllib.request.Request(FFMPEG_DOWNLOAD_URL, headers={"User-Agent": "Baixatudo"})
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=30) as response, archive_path.open("wb") as target:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                check_cancelled()
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                target.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)
                progress = f"{downloaded * 100 // total}%" if total else f"{downloaded // (1024 * 1024)} MB"
                report("status", f"Instalando FFmpeg... {progress}")
        with urllib.request.urlopen(FFMPEG_DOWNLOAD_URL + ".sha256", timeout=30) as response:
            expected = response.read().decode("utf-8").split()[0].lower()
        if digest.hexdigest() != expected:
            raise RuntimeError("Falha na verificacao do FFmpeg. Tente novamente.")
        with zipfile.ZipFile(archive_path) as archive:
            for name in ("ffmpeg.exe", "ffprobe.exe"):
                matches = [entry for entry in archive.namelist() if entry.endswith("/bin/" + name)]
                if len(matches) != 1:
                    raise RuntimeError(f"Pacote FFmpeg invalido: {name} ausente ou duplicado.")
                with archive.open(matches[0]) as source, (staging / name).open("wb") as target:
                    shutil.copyfileobj(source, target)
                subprocess.run([str(staging / name), "-version"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=CREATE_NO_WINDOW, timeout=30)
        check_cancelled()
        for name in ("ffmpeg.exe", "ffprobe.exe"):
            os.replace(staging / name, TOOLS_DIR / name)
    report("log", f"FFmpeg e ffprobe prontos em: {TOOLS_DIR}")
    return str(TOOLS_DIR)


def is_supported_url(text: str) -> bool:
    try:
        parsed = urlparse(text.strip())
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    host = (parsed.hostname or "").lower().strip(".")
    if not host:
        return False

    return (
        host == "youtu.be"
        or host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtube-nocookie.com"
        or host.endswith(".youtube-nocookie.com")
        or host == "pornhub.com"
        or host.endswith(".pornhub.com")
        or host == "xvideos.com"
        or host.endswith(".xvideos.com")
    )


def quality_arguments(option: str) -> list[str]:
    if option == "MP4 ate 1080p":
        return [
            "-f",
            "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/best[height<=1080]",
            "--merge-output-format",
            "mp4",
        ]

    if option == "Melhor qualidade":
        return ["-f", "bv*+ba/b"]

    if option == "Somente audio MP3":
        return ["-x", "--audio-format", "mp3"]

    return ["-f", "best[ext=mp4]/best"]


def output_template(separate_by_site: bool) -> str:
    if separate_by_site:
        return "%(extractor_key)s/%(title).180B [%(id)s].%(ext)s"

    return "%(title).180B [%(id)s].%(ext)s"


class BaixatudoApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Baixatudo")
        self.root.geometry("980x720")
        self.root.minsize(800, 620)
        self.root.configure(bg="#f6f7f9")

        self.ui_queue: queue.Queue[tuple[str, tuple[object, ...]]] = queue.Queue()
        self.stop_event = threading.Event()
        self.process_lock = threading.Lock()
        self.current_process: subprocess.Popen[str] | None = None
        self.busy = False

        self.folder_var = tk.StringVar(value=str(default_download_folder()))
        self.quality_var = tk.StringVar(value=QUALITY_OPTIONS[0])
        self.playlist_var = tk.BooleanVar(value=False)
        self.subfolder_var = tk.BooleanVar(value=True)
        self.permission_var = tk.BooleanVar(value=False)

        self._configure_fonts()
        self._configure_styles()
        self._build_ui()
        self._refresh_engine_status()
        self._append_log("Pronto. Cole links publicos e escolha a pasta de destino.")

        self.root.after(100, self._drain_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_fonts(self) -> None:
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            font = tkfont.nametofont(name)
            font.configure(family="Segoe UI", size=10)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background="#f6f7f9")
        style.configure("TLabel", background="#f6f7f9", foreground="#24292f")
        style.configure("TButton", padding=(12, 7))
        style.configure("Primary.TButton", background="#1f6feb", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#185abc"), ("disabled", "#94a3b8")])
        style.configure("Danger.TButton", background="#b42318", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#8f1b12"), ("disabled", "#94a3b8")])
        style.configure("TCheckbutton", background="#f6f7f9", foreground="#24292f")
        style.configure("Horizontal.TProgressbar", troughcolor="#d0d7de", background="#1f6feb")

    def _build_ui(self) -> None:
        self.container = ttk.Frame(self.root, padding=18)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(2, weight=2)
        self.container.grid_rowconfigure(7, weight=3)

        header = tk.Frame(self.container, bg="#20252c", height=92)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        title = tk.Label(
            header,
            text="Baixatudo",
            bg="#20252c",
            fg="#ffffff",
            font=("Segoe UI", 22, "bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 0))

        subtitle = tk.Label(
            header,
            text="Downloads de links publicos do YouTube, Pornhub e XVideos.",
            bg="#20252c",
            fg="#dae0e7",
            font=("Segoe UI", 10),
            anchor="w",
        )
        subtitle.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 12))

        self.engine_label = ttk.Label(self.container, text="", font=("Segoe UI", 9, "bold"))
        self.engine_label.grid(row=1, column=0, sticky="ew", pady=(10, 6))

        url_frame = ttk.Frame(self.container)
        url_frame.grid(row=2, column=0, sticky="nsew")
        url_frame.grid_columnconfigure(0, weight=1)
        url_frame.grid_rowconfigure(1, weight=1)

        ttk.Label(url_frame, text="Links", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")

        text_frame = ttk.Frame(url_frame)
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 10))
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        self.url_box = tk.Text(
            text_frame,
            height=7,
            wrap="word",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#24292f",
            insertbackground="#24292f",
        )
        self.url_box.grid(row=0, column=0, sticky="nsew")
        url_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.url_box.yview)
        url_scroll.grid(row=0, column=1, sticky="ns")
        self.url_box.configure(yscrollcommand=url_scroll.set)

        folder_frame = ttk.Frame(self.container)
        folder_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        folder_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(folder_frame, text="Pasta", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var)
        self.folder_entry.grid(row=0, column=1, sticky="ew")
        self.browse_button = ttk.Button(folder_frame, text="Escolher", command=self._choose_folder)
        self.browse_button.grid(row=0, column=2, padx=(8, 0))
        self.open_folder_button = ttk.Button(folder_frame, text="Abrir pasta", command=self._open_folder)
        self.open_folder_button.grid(row=0, column=3, padx=(8, 0))

        options_frame = ttk.Frame(self.container)
        options_frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        options_frame.grid_columnconfigure(0, weight=1)

        choices_frame = ttk.Frame(options_frame)
        choices_frame.grid(row=0, column=0, sticky="ew")

        self.quality_combo = ttk.Combobox(
            choices_frame,
            textvariable=self.quality_var,
            values=QUALITY_OPTIONS,
            state="readonly",
            width=22,
        )
        self.quality_combo.grid(row=0, column=0, sticky="w", padx=(0, 14))

        self.playlist_check = ttk.Checkbutton(choices_frame, text="Baixar playlist", variable=self.playlist_var)
        self.playlist_check.grid(row=0, column=1, sticky="w", padx=(0, 14))

        self.subfolder_check = ttk.Checkbutton(choices_frame, text="Separar por site", variable=self.subfolder_var)
        self.subfolder_check.grid(row=0, column=2, sticky="w", padx=(0, 14))

        self.permission_check = ttk.Checkbutton(
            choices_frame,
            text="Tenho permissao para baixar estes links",
            variable=self.permission_var,
        )
        self.permission_check.grid(row=0, column=3, sticky="w", padx=(0, 14))

        buttons_frame = ttk.Frame(options_frame)
        buttons_frame.grid(row=1, column=0, sticky="e", pady=(8, 0))

        self.install_button = ttk.Button(
            buttons_frame,
            text="Instalar/atualizar ferramentas",
            command=lambda: self._run_ui_action(self._install_clicked),
        )
        self.install_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(
            buttons_frame,
            text="Parar",
            style="Danger.TButton",
            command=lambda: self._run_ui_action(self._stop_download),
            state="disabled",
            width=10,
        )
        self.stop_button.grid(row=0, column=1, padx=(0, 8))
        self.download_button = ttk.Button(
            buttons_frame,
            text="Baixar",
            style="Primary.TButton",
            command=lambda: self._run_ui_action(self._download_clicked),
            width=14,
        )
        self.download_button.grid(row=0, column=2)

        status_frame = ttk.Frame(self.container)
        status_frame.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ttk.Label(status_frame, text="Pronto.", font=("Segoe UI", 9, "bold"))
        self.status_label.grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=230)
        self.progress.grid(row=0, column=1, sticky="e")

        ttk.Label(self.container, text="Registro", font=("Segoe UI", 10, "bold")).grid(row=6, column=0, sticky="w")

        log_frame = ttk.Frame(self.container)
        log_frame.grid(row=7, column=0, sticky="nsew", pady=(6, 0))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_box = tk.Text(
            log_frame,
            height=10,
            wrap="word",
            relief="flat",
            borderwidth=0,
            font=("Consolas", 9),
            bg="#12161c",
            fg="#e8eef4",
            insertbackground="#e8eef4",
            state="disabled",
        )
        self.log_box.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_box.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=log_scroll.set)

        self.input_widgets = (
            self.url_box,
            self.folder_entry,
            self.browse_button,
            self.open_folder_button,
            self.quality_combo,
            self.playlist_check,
            self.subfolder_check,
            self.permission_check,
            self.install_button,
            self.download_button,
        )

    def _send(self, kind: str, *values: object) -> None:
        self.ui_queue.put((kind, values))

    def _run_ui_action(self, action) -> None:
        try:
            action()
        except Exception as exc:
            self._set_status("Erro.")
            self._append_log(f"Erro na acao: {exc}")
            self._append_log(traceback.format_exc())
            messagebox.showerror(
                "Baixatudo",
                f"Algo impediu esta acao.\n\n{exc}",
                parent=self.root,
            )

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, values = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._append_log(str(values[0]))
            elif kind == "status":
                self._set_status(str(values[0]))
            elif kind == "busy":
                self._set_busy(bool(values[0]), str(values[1]), bool(values[2]))
            elif kind == "engine":
                self._refresh_engine_status()
            elif kind == "message":
                level, title, body = values
                if level == "error":
                    messagebox.showerror(str(title), str(body), parent=self.root)
                elif level == "warning":
                    messagebox.showwarning(str(title), str(body), parent=self.root)
                else:
                    messagebox.showinfo(str(title), str(body), parent=self.root)

        self.root.after(100, self._drain_queue)

    def _append_log(self, message: str) -> None:
        if not message:
            return

        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{message.rstrip()}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def _set_busy(self, busy: bool, status: str, can_stop: bool = False) -> None:
        self.busy = busy
        self._set_status(status)

        for widget in self.input_widgets:
            widget.configure(state="disabled" if busy else "normal")

        if not busy:
            self.quality_combo.configure(state="readonly")

        self.stop_button.configure(state="normal" if busy and can_stop else "disabled")

        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _refresh_engine_status(self) -> None:
        path = find_yt_dlp()
        if path:
            ffmpeg_status = "FFmpeg pronto" if find_ffmpeg() else "FFmpeg sera instalado quando necessario"
            self.engine_label.configure(text=f"Motor pronto | {ffmpeg_status}", foreground="#1a743a")
        else:
            self.engine_label.configure(
                text="Motor nao instalado. Use Instalar/atualizar ferramentas.",
                foreground="#9a5b13",
            )

    def _choose_folder(self) -> None:
        chosen = filedialog.askdirectory(parent=self.root, initialdir=self.folder_var.get() or str(Path.home()))
        if chosen:
            self.folder_var.set(chosen)

    def _open_folder(self) -> None:
        folder = Path(os.path.expandvars(self.folder_var.get())).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            messagebox.showwarning("Baixatudo", f"Nao foi possivel abrir a pasta.\n\n{exc}", parent=self.root)

    def _install_clicked(self) -> None:
        if self.busy:
            return

        self._set_busy(True, "Instalando ferramentas...")
        thread = threading.Thread(target=self._install_worker, daemon=True)
        thread.start()

    def _install_worker(self) -> None:
        self._send("busy", True, "Instalando yt-dlp...", False)
        temp_path = YTDLP_LOCAL.with_name("yt-dlp.exe.download")

        try:
            TOOLS_DIR.mkdir(parents=True, exist_ok=True)
            self._send("log", "Baixando yt-dlp do repositorio oficial.")

            request = urllib.request.Request(YTDLP_DOWNLOAD_URL, headers={"User-Agent": "Baixatudo"})
            with urllib.request.urlopen(request, timeout=120) as response:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                with temp_path.open("wb") as file:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            percent = int(downloaded * 100 / total)
                            self._send("status", f"Instalando yt-dlp... {percent}%")

            os.replace(temp_path, YTDLP_LOCAL)
            self._send("log", f"yt-dlp pronto em: {YTDLP_LOCAL}")
            ensure_ffmpeg(self._send)
            self._send("status", "Pronto.")
        except Exception as exc:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass
            self._send("log", f"Falha ao instalar ferramentas: {exc}")
            self._send(
                "message",
                "warning",
                "Baixatudo",
                "Nao foi possivel instalar todas as ferramentas.\n\nVerifique o registro e tente novamente.",
            )
        finally:
            self._send("engine")
            self._send("busy", False, "Pronto.", False)

    def _download_clicked(self) -> None:
        self._append_log("Botao Baixar acionado.")

        if self.busy:
            self._set_status("Aguarde a tarefa atual terminar.")
            return

        if not self.permission_var.get():
            self._set_status("Confirme a permissao para baixar.")
            self._append_log("Download nao iniciado: confirmacao de permissao pendente.")
            confirmed = messagebox.askyesno(
                "Baixatudo",
                "Voce confirma que tem permissao para baixar estes links?",
                parent=self.root,
            )
            if not confirmed:
                return
            self.permission_var.set(True)
            self._append_log("Permissao confirmada.")

        urls = [line.strip() for line in self.url_box.get("1.0", "end").splitlines() if line.strip()]
        if not urls:
            self._set_status("Cole pelo menos um link.")
            self._append_log("Download nao iniciado: nenhum link informado.")
            messagebox.showinfo("Baixatudo", "Cole pelo menos um link.", parent=self.root)
            return

        unsupported = [url for url in urls if not is_supported_url(url)]
        if unsupported:
            self._set_status("Link nao suportado.")
            self._append_log("Download nao iniciado: link fora dos sites aceitos.")
            messagebox.showwarning(
                "Baixatudo",
                "Estes links nao sao de YouTube, Pornhub ou XVideos:\n\n" + "\n".join(unsupported),
                parent=self.root,
            )
            return

        engine = find_yt_dlp()
        if not engine:
            self._set_status("Instale o yt-dlp para continuar.")
            self._append_log("Download nao iniciado: yt-dlp nao encontrado.")
            install_now = messagebox.askyesno(
                "Baixatudo",
                "O yt-dlp ainda nao esta instalado.\n\nDeseja instalar agora?",
                parent=self.root,
            )
            if install_now:
                self._install_clicked()
            return

        folder = Path(os.path.expandvars(self.folder_var.get())).expanduser()
        if folder.exists() and not folder.is_dir():
            self._set_status("Pasta de destino invalida.")
            self._append_log("Download nao iniciado: destino nao e uma pasta.")
            messagebox.showwarning("Baixatudo", "Escolha uma pasta de destino valida.", parent=self.root)
            return

        self.stop_event.clear()
        quality = self.quality_var.get()
        playlist = self.playlist_var.get()
        separate_by_site = self.subfolder_var.get()

        thread = threading.Thread(
            target=self._download_worker,
            args=(engine, urls, folder, quality, playlist, separate_by_site),
            daemon=True,
        )
        self._set_busy(True, "Preparando download...", True)
        thread.start()

    def _download_worker(
        self,
        engine: str,
        urls: list[str],
        folder: Path,
        quality: str,
        playlist: bool,
        separate_by_site: bool,
    ) -> None:
        self._send("busy", True, "Baixando...", True)
        completed = 0
        failed = 0

        try:
            folder.mkdir(parents=True, exist_ok=True)
            self._send("log", "Use apenas conteudo proprio, autorizado e permitido pelos termos do site.")

            if quality in FFMPEG_QUALITY_OPTIONS:
                ensure_ffmpeg(self._send, self.stop_event)
                self._send("engine")

            for index, url in enumerate(urls, start=1):
                if self.stop_event.is_set():
                    break

                self._send("status", f"Baixando {index}/{len(urls)}...")
                exit_code = self._run_yt_dlp(engine, url, folder, quality, playlist, separate_by_site)

                if self.stop_event.is_set():
                    break

                if exit_code == 0:
                    completed += 1
                    self._send("log", f"Concluido: {url}")
                else:
                    failed += 1
                    self._send("log", f"Falhou com codigo {exit_code}: {url}")

            if self.stop_event.is_set():
                self._send("status", "Download interrompido.")
                self._send("log", "Download interrompido pelo usuario.")
            elif failed:
                self._send("status", f"Concluido com falhas: {completed} sucesso(s), {failed} falha(s).")
            else:
                self._send("status", f"Concluido: {completed} arquivo(s).")
                self._send("log", f"Arquivos salvos em: {folder}")
        except InterruptedError:
            self._send("log", "Download interrompido pelo usuario.")
        except Exception as exc:
            self._send("status", "Erro durante o download.")
            self._send("log", f"Erro: {exc}")
        finally:
            with self.process_lock:
                self.current_process = None
            self.stop_event.clear()
            self._send("busy", False, "Pronto.", False)

    def _run_yt_dlp(
        self,
        engine: str,
        url: str,
        folder: Path,
        quality: str,
        playlist: bool,
        separate_by_site: bool,
    ) -> int:
        args = [
            engine,
            "--newline",
            "--windows-filenames",
            "--no-warnings",
            "-P",
            str(folder),
            "-o",
            output_template(separate_by_site),
        ]

        if not playlist:
            args.append("--no-playlist")

        ffmpeg_location = find_ffmpeg()
        if ffmpeg_location:
            args.extend(["--ffmpeg-location", ffmpeg_location])
        args.extend(quality_arguments(quality))
        args.append(url)

        self._send("log", f"Iniciando: {url}")

        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        with self.process_lock:
            self.current_process = process

        try:
            if process.stdout:
                for line in process.stdout:
                    self._send("log", line.rstrip())
                    if self.stop_event.is_set():
                        self._kill_current_process()
                        break

            return process.wait()
        finally:
            with self.process_lock:
                if self.current_process is process:
                    self.current_process = None

    def _stop_download(self) -> None:
        if not self.busy:
            return

        self.stop_event.set()
        self._set_status("Parando...")
        self._append_log("Parando download atual...")
        self._kill_current_process()

    def _kill_current_process(self) -> None:
        with self.process_lock:
            process = self.current_process

        if not process or process.poll() is not None:
            return

        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW,
                    check=False,
                )
            else:
                process.terminate()
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def _on_close(self) -> None:
        if self.busy:
            close_now = messagebox.askyesno(
                "Baixatudo",
                "Existe uma tarefa em andamento. Deseja parar e fechar?",
                parent=self.root,
            )
            if not close_now:
                return
            self.stop_event.set()
            self._kill_current_process()

        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    BaixatudoApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        try:
            messagebox.showerror("Baixatudo", f"O app nao conseguiu iniciar.\n\n{exc}")
        except Exception:
            raise
