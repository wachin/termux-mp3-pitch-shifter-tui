#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Termux MP3 Pitch Shifter (TUI) v6
=================================
- Interfaz de terminal para Termux para subir/bajar tono de MP3.
- Muestra textos largos en varias líneas.
- Conserva metadatos y trata de conservar portada.
- Intenta conservar bitrate, sample rate y canales.

Correcciones respecto a v3/v4/v5:
- Usa select() para I/O no bloqueante → la animación pulse funciona.
- Parseo correcto de out_time_us (µs) y out_time_ms (ms) por nombre de clave.
- Throttling de renderizado (máx. 1 redraw cada 200 ms) → sin parpadeo.
- Usa -progress pipe:1 (stdout) para datos limpios de progreso.
- stderr se captura aparte para errores.
"""

import curses
import locale
import os
import select
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import List, Optional, Tuple

locale.setlocale(locale.LC_ALL, "")

SEMITONE_OPTIONS = [-7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7]

# --- Intervalo mínimo entre redraws (segundos) ---
RENDER_INTERVAL = 0.2


def semitone_to_factor(semitones: int) -> float:
    return 2 ** (semitones / 12)


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def check_dependencies() -> Tuple[bool, str]:
    if shutil.which("ffmpeg") is None:
        return False, "No se encontró ffmpeg en PATH."
    if shutil.which("ffprobe") is None:
        return False, "No se encontró ffprobe en PATH."

    rc, out, err = run_cmd(["ffmpeg", "-filters"])
    combined = (out or "") + "\n" + (err or "")
    if "rubberband" not in combined:
        return False, "No aparece el filtro rubberband en ffmpeg -filters."

    return True, "Dependencias correctas."


def list_mp3_files(folder: Path) -> List[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"],
        key=lambda p: p.name.lower(),
    )


def ffprobe_value(
    path: Path, entry: str, select_streams: Optional[str] = "a:0"
) -> Optional[str]:
    cmd = ["ffprobe", "-v", "error"]
    if select_streams is not None:
        cmd += ["-select_streams", select_streams]
    cmd += [
        "-show_entries", entry,
        "-of", "default=nokey=1:noprint_wrappers=1",
        str(path),
    ]
    rc, out, _ = run_cmd(cmd)
    if rc != 0:
        return None
    value = out.strip()
    return value if value else None


def get_duration_seconds(path: Path) -> Optional[float]:
    value = ffprobe_value(path, "format=duration", select_streams=None)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def has_cover_art(path: Path) -> bool:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v",
        "-show_entries", "stream=index,codec_name,disposition",
        "-of", "default=nokey=0:noprint_wrappers=1",
        str(path),
    ]
    rc, out, _ = run_cmd(cmd)
    if rc != 0:
        return False
    return "index=" in out.lower()


def get_audio_info(path: Path) -> dict:
    bitrate = ffprobe_value(path, "stream=bit_rate")
    samplerate = ffprobe_value(path, "stream=sample_rate")
    channels = ffprobe_value(path, "stream=channels")
    duration = get_duration_seconds(path)

    return {
        "bitrate": int(bitrate) if bitrate and bitrate.isdigit() else None,
        "sample_rate": int(samplerate) if samplerate and samplerate.isdigit() else None,
        "channels": int(channels) if channels and channels.isdigit() else None,
        "has_cover": has_cover_art(path),
        "duration": duration,
    }


def build_output_name(input_path: Path, semitones: int) -> Path:
    sign = "+" if semitones > 0 else ""
    return input_path.with_name(f"{input_path.stem} {sign}{semitones}.mp3")


def secs_to_hms(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_time_hms(value: str) -> Optional[float]:
    """Parsea HH:MM:SS.ss a segundos."""
    try:
        parts = value.strip().split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    except Exception:
        pass
    return None


def wrap_text(text: str, width: int) -> List[str]:
    if width <= 1:
        return [text[: max(0, width)]]
    lines = []
    for part in text.splitlines() or [""]:
        wrapped = textwrap.wrap(
            part,
            width=width,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False,
        )
        if wrapped:
            lines.extend(wrapped)
        else:
            lines.append("")
    return lines


def make_labeled_block(label: str, value: str, width: int) -> List[str]:
    out = [f"{label}:"]
    out.extend(wrap_text(value, width))
    return out


def draw_box(stdscr, y, x, h, w, title=""):
    for i in range(x, x + w):
        stdscr.addch(y, i, curses.ACS_HLINE)
        stdscr.addch(y + h - 1, i, curses.ACS_HLINE)
    for i in range(y, y + h):
        stdscr.addch(i, x, curses.ACS_VLINE)
        stdscr.addch(i, x + w - 1, curses.ACS_VLINE)

    stdscr.addch(y, x, curses.ACS_ULCORNER)
    stdscr.addch(y, x + w - 1, curses.ACS_URCORNER)
    stdscr.addch(y + h - 1, x, curses.ACS_LLCORNER)
    stdscr.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)

    if title:
        stdscr.addstr(y, x + 2, f"[ {title} ]"[: max(0, w - 4)])


def trim_text(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if len(text) <= max_width:
        return text
    if max_width == 1:
        return text[:1]
    return text[: max_width - 1] + "\u2026"


def menu_select(stdscr, title: str, items: List[str], footer: str) -> int:
    curses.curs_set(0)
    idx = 0
    scroll = 0

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        box_h = max(6, h - 1)
        box_w = max(20, w)
        draw_box(stdscr, 0, 0, box_h, box_w, title=title)

        visible_h = max(1, box_h - 4)
        if idx < scroll:
            scroll = idx
        elif idx >= scroll + visible_h:
            scroll = idx - visible_h + 1

        for row in range(visible_h):
            item_i = scroll + row
            if item_i >= len(items):
                break
            attr = curses.A_REVERSE if item_i == idx else curses.A_NORMAL
            stdscr.addstr(2 + row, 2, trim_text(items[item_i], box_w - 4), attr)

        stdscr.addstr(box_h - 1, 1, trim_text(footer, box_w - 2))
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), 27):
            return -1
        if key in (curses.KEY_UP, ord("k")):
            idx = (idx - 1) % len(items)
        elif key in (curses.KEY_DOWN, ord("j")):
            idx = (idx + 1) % len(items)
        elif key in (10, 13, curses.KEY_ENTER):
            return idx


def message_screen(stdscr, title: str, text: str):
    scroll = 0
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        box_h = max(6, h - 1)
        box_w = max(20, w)
        draw_box(stdscr, 0, 0, box_h, box_w, title=title)

        wrapped_lines = wrap_text(text, box_w - 4)
        max_lines = max(1, box_h - 4)
        scroll = max(0, min(scroll, max(0, len(wrapped_lines) - max_lines)))

        for i, line in enumerate(wrapped_lines[scroll : scroll + max_lines]):
            stdscr.addstr(2 + i, 2, trim_text(line, box_w - 4))

        stdscr.addstr(
            box_h - 1, 1, trim_text("\u2191\u2193 desplazar | Enter continuar | q salir", box_w - 2)
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (10, 13, curses.KEY_ENTER, ord("q"), 27):
            break
        elif key in (curses.KEY_UP, ord("k")):
            scroll = max(0, scroll - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            scroll = min(max(0, len(wrapped_lines) - max_lines), scroll + 1)


def render_progress_screen(
    stdscr,
    file_name: str,
    semitones: int,
    bitrate_text: str,
    progress_pct: float,
    wall_elapsed_sec: float,
    eta_sec: Optional[float],
    current_time_sec: float,
    total_sec: Optional[float],
    pulse: int = 0,
):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    box_h = max(10, h - 1)
    box_w = max(20, w)
    draw_box(stdscr, 0, 0, box_h, box_w, title="Procesando")

    lines = []
    lines.extend(make_labeled_block("Archivo", file_name, box_w - 4))
    lines.append("")
    lines.append(f"Cambio: {semitones:+d} semitonos")
    lines.extend(make_labeled_block("Bitrate", bitrate_text, box_w - 4))
    lines.append("")

    available_bar_width = max(10, box_w - 10)
    if progress_pct > 0:
        filled = int(round((progress_pct / 100.0) * available_bar_width))
    else:
        # Animación pulse cuando no hay datos de progreso aún
        filled = pulse % max(1, available_bar_width)
    filled = max(0, min(available_bar_width, filled))
    bar = "[" + "#" * filled + "-" * (available_bar_width - filled) + "]"

    lines.append(f"Progreso: {progress_pct:5.1f}%")
    lines.append(bar)

    if total_sec:
        lines.append(
            f"Audio procesado: {secs_to_hms(current_time_sec)} / {secs_to_hms(total_sec)}"
        )
    else:
        lines.append(f"Audio procesado: {secs_to_hms(current_time_sec)}")

    lines.append(f"Tiempo transcurrido: {secs_to_hms(wall_elapsed_sec)}")
    if eta_sec is not None:
        lines.append(f"Tiempo restante aprox.: {secs_to_hms(eta_sec)}")
    else:
        lines.append("Tiempo restante aprox.: calculando...")

    max_lines = max(1, box_h - 4)
    for i, line in enumerate(lines[:max_lines]):
        stdscr.addstr(2 + i, 2, trim_text(line, box_w - 4))

    stdscr.addstr(box_h - 1, 1, trim_text("Procesando... espera por favor", box_w - 2))
    stdscr.refresh()


def parse_progress_line(line: str, state: dict):
    """
    Parsea una línea del formato -progress de FFmpeg (key=value).
    Actualiza el diccionario `state` con los valores encontrados.
    """
    if "=" not in line:
        return False

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if key == "out_time_us":
        # Microsegundos → segundos
        try:
            state["current_time_sec"] = int(value) / 1_000_000.0
        except (ValueError, TypeError):
            pass
        return True

    elif key == "out_time_ms":
        # Milisegundos → segundos
        try:
            state["current_time_sec"] = int(value) / 1000.0
        except (ValueError, TypeError):
            pass
        return True

    elif key == "out_time":
        # Formato HH:MM:SS.ss
        parsed = parse_time_hms(value)
        if parsed is not None:
            state["current_time_sec"] = parsed
        return True

    elif key == "speed":
        try:
            state["speed"] = float(value.rstrip("x").strip())
        except (ValueError, TypeError):
            pass
        return True

    elif key == "progress":
        state["progress_flag"] = value
        return True

    elif key == "total_size" or key == "bitrate" or key == "fps":
        # Otros campos que no necesitamos para la barra
        return True

    return False


def transcode_pitch_with_progress(
    stdscr, input_path: Path, semitones: int
) -> Tuple[bool, str]:
    factor = semitone_to_factor(semitones)
    info = get_audio_info(input_path)
    output_path = build_output_name(input_path, semitones)

    # --- Construir comando FFmpeg ---
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-nostats",
        "-loglevel", "warning",
        "-progress", "pipe:1",           # Progreso estructurado por stdout
        "-i", str(input_path),
        "-map_metadata", "0",
        "-map", "0:a:0",
        "-af", f"rubberband=pitch={factor:.6f}",
        "-c:a", "libmp3lame",
        "-id3v2_version", "3",
        "-write_id3v1", "1",
    ]

    if info["has_cover"]:
        cmd += ["-map", "0:v?", "-c:v", "copy", "-disposition:v", "attached_pic"]

    if info["bitrate"]:
        kbps = max(32, round(info["bitrate"] / 1000))
        cmd += ["-b:a", f"{kbps}k"]
        bitrate_text = f"{kbps} kbps (aprox. igual al original)"
    else:
        cmd += ["-q:a", "2"]
        bitrate_text = "VBR alta, q=2"

    if info["sample_rate"]:
        cmd += ["-ar", str(info["sample_rate"])]
    if info["channels"]:
        cmd += ["-ac", str(info["channels"])]

    cmd.append(str(output_path))

    # --- Variables de estado ---
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,       # bytes para select
        bufsize=0,        # sin buffering del sistema
    )

    # Asegurar que stdout y stderr sean file descriptors reales para select
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()

    start_wall = time.time()
    last_render_time = 0.0
    pulse = 0

    state = {
        "current_time_sec": 0.0,
        "speed": None,
        "progress_flag": "continue",
    }

    total_sec = info["duration"]
    eta_sec = None
    stderr_chunks = []

    # --- Pantalla inicial ---
    render_progress_screen(
        stdscr,
        file_name=input_path.name,
        semitones=semitones,
        bitrate_text=bitrate_text,
        progress_pct=0.0,
        wall_elapsed_sec=0.0,
        eta_sec=None,
        current_time_sec=0.0,
        total_sec=total_sec,
        pulse=pulse,
    )
    last_render_time = time.time()

    # --- Loop principal con I/O no bloqueante ---
    try:
        while True:
            # select con timeout de 100ms → permite animación pulse
            try:
                ready_read, _, _ = select.select(
                    [stdout_fd, stderr_fd], [], [], 0.1
                )
            except (ValueError, OSError):
                # fd cerrado → salir del loop
                break

            # Leer stdout (datos de progreso)
            if stdout_fd in ready_read:
                raw_line = process.stdout.readline()
                if not raw_line:
                    # EOF en stdout → FFmpeg terminó de escribir progreso
                    pass
                else:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line:
                        parse_progress_line(line, state)

            # Leer stderr (mensajes de error/warning)
            if stderr_fd in ready_read:
                raw_line = process.stderr.readline()
                if not raw_line:
                    pass
                else:
                    stderr_chunks.append(raw_line)

            # Verificar si el proceso terminó
            if process.poll() is not None:
                # Proceso terminado: leer cualquier dato restante
                while True:
                    raw_line = process.stdout.readline()
                    if not raw_line:
                        break
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line:
                        parse_progress_line(line, state)

                while True:
                    raw_line = process.stderr.readline()
                    if not raw_line:
                        break
                    stderr_chunks.append(raw_line)
                break

            # --- Calcular progreso y ETA ---
            current_time_sec = state["current_time_sec"]
            last_speed = state["speed"]
            wall_elapsed_sec = time.time() - start_wall

            if total_sec and total_sec > 0 and current_time_sec > 0:
                progress_pct = max(0.0, min(100.0, (current_time_sec / total_sec) * 100.0))
            else:
                progress_pct = 0.0

            if (
                last_speed
                and last_speed > 0
                and total_sec
                and total_sec > 0
                and current_time_sec > 0
            ):
                remaining_audio = max(0.0, total_sec - current_time_sec)
                eta_sec = remaining_audio / last_speed
            elif current_time_sec > 0 and wall_elapsed_sec > 2 and total_sec and total_sec > 0:
                avg_speed = current_time_sec / wall_elapsed_sec
                remaining_audio = max(0.0, total_sec - current_time_sec)
                eta_sec = remaining_audio / avg_speed if avg_speed > 0 else None

            # --- Renderizar con throttling ---
            now = time.time()
            if now - last_render_time >= RENDER_INTERVAL:
                if progress_pct == 0:
                    pulse += 1
                render_progress_screen(
                    stdscr,
                    file_name=input_path.name,
                    semitones=semitones,
                    bitrate_text=bitrate_text,
                    progress_pct=progress_pct,
                    wall_elapsed_sec=wall_elapsed_sec,
                    eta_sec=eta_sec,
                    current_time_sec=current_time_sec,
                    total_sec=total_sec,
                    pulse=pulse,
                )
                last_render_time = now

    except KeyboardInterrupt:
        process.kill()
        process.wait()
        return False, "Proceso cancelado por el usuario."

    rc = process.wait()

    # --- Render final al 100% ---
    render_progress_screen(
        stdscr,
        file_name=input_path.name,
        semitones=semitones,
        bitrate_text=bitrate_text,
        progress_pct=100.0 if rc == 0 else progress_pct,
        wall_elapsed_sec=time.time() - start_wall,
        eta_sec=0.0,
        current_time_sec=total_sec if total_sec else current_time_sec,
        total_sec=total_sec,
    )

    stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace")

    if rc == 0:
        quality_note = (
            f"mismo bitrate aproximado ({round(info['bitrate']/1000)} kbps)"
            if info["bitrate"]
            else "calidad VBR alta (q=2)"
        )
        cover_note = "si" if info["has_cover"] else "no detectada"
        return True, (
            f"Creado:\n{output_path.name}\n\n"
            f"Tono:\n{semitones:+d} semitonos\n"
            f"Factor:\n{factor:.6f}\n"
            f"Salida:\n{quality_note}\n"
            f"Portada:\n{cover_note}"
        )

    return False, f"FFmpeg devolvio error (codigo {rc}):\n\n{stderr_text[-5000:]}"


def app(stdscr, folder: Path):
    ok, msg = check_dependencies()
    if not ok:
        message_screen(stdscr, "Error", msg)
        return

    while True:
        mp3_files = list_mp3_files(folder)
        if not mp3_files:
            message_screen(
                stdscr,
                "Sin MP3",
                f"No se encontraron archivos .mp3 en:\n{folder}\n\n"
                f"Ejemplo:\npython termux_pitch_tui_v6.py /sdcard/Music",
            )
            return

        sel = menu_select(
            stdscr,
            f"Archivos MP3 - {folder}",
            [p.name for p in mp3_files],
            "\u2191\u2193 mover | Enter elegir archivo | q salir",
        )
        if sel < 0:
            return

        selected_file = mp3_files[sel]
        semitone_items = [
            f"{n:+d} semitono{'s' if abs(n) != 1 else ''}" for n in SEMITONE_OPTIONS
        ]

        sem_sel = menu_select(
            stdscr,
            f"Tono para: {selected_file.name}",
            semitone_items,
            "\u2191\u2193 mover | Enter procesar | q cancelar",
        )
        if sem_sel < 0:
            continue

        semitones = SEMITONE_OPTIONS[sem_sel]
        success, result_text = transcode_pitch_with_progress(
            stdscr, selected_file, semitones
        )
        message_screen(stdscr, "Exito" if success else "Error", result_text)


def main():
    folder = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.cwd()
    try:
        curses.wrapper(app, folder)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
