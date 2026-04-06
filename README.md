# Termux MP3 Pitch Shifter (TUI)

Una herramienta de interfaz de terminal (TUI) para Android (Termux) que permite modificar el tono (pitch) de archivos MP3 de forma sencilla y visual.

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Android-green?logo=android)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Características Principales

- **Interfaz TUI Interactiva:** Menús navegables mediante teclas direccionales gracias a la librería `curses`.
- **Cambio de Tono (Pitch Shifting):** Sube o baja el tono de -7 a +7 semitonos sin alterar la velocidad de reproducción.
- **Preservación de Calidad:** Intenta mantener el *bitrate*, *sample rate* y canales del archivo original.
- **Metadatos y Portada:** Conserva las etiquetas ID3 y la imagen de portada del archivo MP3 original.
- **Barra de Progreso en Tiempo Real:** Muestra el porcentaje de avance, tiempo transcurrido y tiempo restante estimado (ETA).
- **Procesamiento Limpio:** Uso de `rubberband` para un estiramiento de tiempo de alta calidad.

## Requisitos Previos

Antes de ejecutar el script, necesitas tener instalado **Termux** en tu dispositivo Android pero no desde la Play Store sino siguiendo este tutorial:

[https://github.com/wachin/Linux-on-Android-with-Termux](https://github.com/wachin/Linux-on-Android-with-Termux)

y configurar el entorno:

1.  **Actualizar paquetes:**
    ```bash
    pkg update && pkg upgrade
    ```

2.  **Instalar Python:**
    ```bash
    pkg install python
    ```

3.  **Instalar FFmpeg (con soporte para librubberband):**
    Es importante tener una versión de FFmpeg que incluya el filtro `rubberband`.
    ```bash
    pkg install ffmpeg
    ```

4.  **Permisos de Almacenamiento (Opcional pero recomendado):**
    Para acceder a la carpeta de música de tu dispositivo (`/sdcard/Music`).
    ```bash
    termux-setup-storage
    ```

## Instalación y Uso

1.  **Descargar el script:**
    Clona este repositorio o descarga el archivo `termux_pitch_tui_v6.py` directamente.

    ```bash
    git clone https://github.com/wachin/termux-mp3-pitch-shifter-tui
    cd termux-mp3-pitch-shifter-tui
    ```

2.  **Ejecutar el script:**
    Puedes ejecutarlo sin argumentos para procesar archivos en el directorio actual:
    ```bash
    python termux_pitch_tui_v6.py
    ```

    O especificar una ruta de carpeta directamente:
    ```bash
    python termux_pitch_tui_v6.py /sdcard/Music/MiCarpeta
    ```

## Controles

Dentro de la interfaz, utiliza las siguientes teclas:

| Tecla         | Acción                           |
|---------------|----------------------------------|
| `↑` / `k`     | Mover selección hacia arriba     |
| `↓` / `j`     | Mover selección hacia abajo      |
| `Enter`       | Seleccionar archivo / Confirmar  |
| `q` / `Esc`   | Salir / Volver / Cancelar        |

## Cómo Funciona (Detalles Técnicos)

El script utiliza `curses` para dibujar la interfaz en la terminal y `subprocess` para interactuar con `ffmpeg` y `ffprobe`.

- **Análisis:** Utiliza `ffprobe` para detectar automáticamente si el MP3 tiene portada, su duración, bitrate y tasa de muestreo.
- **Procesamiento:** Construye un comando complejo de `ffmpeg` que incluye:
  - Filtro `rubberband=pitch=factor` para el cambio de tono.
  - Mapeo de streams para conservar audio y video (portada).
  - `select()` y I/O no bloqueante para leer el progreso de `ffmpeg` en tiempo real sin congelar la interfaz.
- **Salida:** Genera un nuevo archivo con el sufijo del tono aplicado (ej. `cancion +2.mp3`).

## Notas de la Versión (v6)

Esta versión incluye mejoras significativas respecto a versiones anteriores:
- **I/O No bloqueante:** Implementación de `select()` para que la animación de carga ('pulse') funcione correctamente mientras FFmpeg procesa.
- **Parseo Robustecido:** Corrección en la lectura de tiempos (`out_time_us` vs `out_time_ms`) para evitar errores de progreso.
- **Anti-Parpadeo:** Throttling de renderizado (máx. 1 redibujado cada 200ms) para una experiencia visual fluida.

## Licencia

Este proyecto se distribuye bajo la Licencia MIT. Siéntete libre de modificarlo y mejorarlo.

---

**Desarrollado para Termux ❤️**
