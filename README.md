# Termux MP3 Pitch Shifter (TUI)

Una herramienta de interfaz de terminal (TUI) para Android (Termux) que permite modificar el tono (pitch) de archivos MP3 de forma sencilla y visual.

**Nota:** También se puede ejecutar en Linux

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
    Es importante tener una versión de FFmpeg que incluya el filtro `rubberband`, la versión de Termux indicada en el tutorial lo tiene
    ```bash
    pkg install ffmpeg
    ```

4.  **Permisos de Almacenamiento (Opcional pero recomendado):**
    Para acceder a la carpeta de música de tu dispositivo (`/sdcard/Music`).
    ```bash
    termux-setup-storage
    ```
    
## Limitaciones, sólo mp3 por los metadatos

El script usa banderas específicas para etiquetas ID3v2 (típicas de MP3), como `-id3v2_version 3` y `-write_id3v1 1`. Otros formatos como M4A o FLAC usan sistemas de metadatos diferentes (como el contenedor MP4 o Vorbis Comments), por lo que la conservación de portadas y títulos podría fallar si no se ajusta el código para otro formato de audio.

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
    python termux_pitch_tui.py
    ```
    
y allí al lado deben estar el o los archivos mp3

### Cómo ejecutarlo en Linux

Ejemplo para ejecutarlo en MX Linux 23 hay que instalar FFmpeg así:

```bash
sudo apt install ffmpeg
```

y no se preocupe por python pues ya viene por defecto instalado, y para ejecutarlo poner así en una terminal en un directorio donde al lado esté un mp3:

```bash
python3 termux_pitch_tui.py
```

## Controles

Dentro de la interfaz, utiliza las siguientes teclas:

| Tecla         | Acción                           |
|---------------|----------------------------------|
| `↑` / `k`     | Mover selección hacia arriba     |
| `↓` / `j`     | Mover selección hacia abajo      |
| `Enter`       | Seleccionar archivo / Confirmar  |
| `q` / `Esc`   | Salir / Volver / Cancelar        |

## Selecciona un mp3 y baja o sube de semitono

Lo que ves ahí es el menú donde debes elegir cuánto quieres subir o bajar el tono de la canción que seleccionaste. 

El script permite ajustar el tono en un rango de ±7 semitonos: 

```bash
-7 semitonos
-6 semitonos
-5 semitonos
-4 semitonos
-3 semitonos
-2 semitonos
-1 semitono
+1 semitono
+2 semitonos
+3 semitonos
+4 semitonos
+5 semitonos
+6 semitonos
+7 semitonos
```
     
**Las opciones: **

* Los números negativos (ej. -2 semitonos) hacen que la canción suene más grave (más baja).
* Los números positivos (ej. +2 semitonos) hacen que la canción suene más aguda (más alta).
* Nota: Un semitono es la unidad mínima de cambio en música (como pasar de una tecla blanca a una negra adyacente en el piano).
          

**Cómo moverte: **

* Usa las flechas del teclado (Arriba ↑ / Abajo ↓) para resaltar la opción que desees.
* Presiona Enter para comenzar el procesamiento con ese tono.
          
**Cómo salir: **

* Si te arrepentiste, presiona la tecla q para volver al menú anterior.
                     

## Cómo Funciona por dentro (Detalles Técnicos)

El script utiliza `curses` para dibujar la interfaz en la terminal y `subprocess` para interactuar con `ffmpeg` y `ffprobe`.

- **Análisis:** Utiliza `ffprobe` para detectar automáticamente si el MP3 tiene portada, su duración, bitrate y tasa de muestreo.
- **Procesamiento:** Construye un comando complejo de `ffmpeg` que incluye:
  - Filtro `rubberband=pitch=factor` para el cambio de tono.
  - Mapeo de streams para conservar audio y video (portada).
  - `select()` y I/O no bloqueante para leer el progreso de `ffmpeg` en tiempo real sin congelar la interfaz.
- **Salida:** Genera un nuevo archivo con el sufijo del tono aplicado (ej. `cancion +2.mp3`).

## Licencia

Este proyecto se distribuye bajo la Licencia GPL 3. Siéntete libre de modificarlo y mejorarlo.

---

**Desarrollado para Termux ❤️**
