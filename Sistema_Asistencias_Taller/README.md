# Taller Mecánico – Sistema de Asistencias con Reconocimiento Facial

Sistema de control de asistencia para el personal de un taller mecánico. Identifica a los mecánicos por su rostro y registra automáticamente nombre, fecha y hora de ingreso en un archivo CSV.

## Estructura

```
Sistema_Asistencias_Taller/
├── comparacion_rostros.py     # Script 1: compara dos fotos (control vs. prueba)
├── asistencia_taller.py       # Script 2: asistencia con cámara web (una captura)
├── interfaz_taller.py         # Script 3: interfaz gráfica con reconocimiento en tiempo real
├── registro_asistencias.csv   # Registro de ingresos (nombre, fecha, hora_ingreso)
├── Mecanicos/                 # Base de datos: una foto por mecánico ("Nombre Apellido.jpg")
├── Fotos_Prueba/              # FotoA, FotoB y FotoC para probar el Script 1
└── requirements.txt
```

## Librerías

| Librería | Uso |
|---|---|
| `cv2` (OpenCV) | Procesar imágenes, capturar desde la cámara web, dibujar rectángulos y texto |
| `face_recognition` | Cargar imágenes, detectar y codificar rostros, comparar y calcular distancias |
| `os` | Manejo de archivos y carpetas; listar las fotos de los mecánicos y extraer sus nombres |
| `numpy` | Buscar el índice de la menor distancia entre rostros (`argmin`) |
| `datetime` | Fecha y hora actual para registrar cada ingreso |

Instalación: ver `INSTALACION.md` (usa `dlib-bin` para no tener que compilar `dlib`).

## Uso

```bash
python comparacion_rostros.py     # Script 1
python asistencia_taller.py       # Script 2 (cámara web)
python interfaz_taller.py         # Script 3 (interfaz + video en vivo)
python asistencia_taller.py --imagen Fotos_Prueba/FotoA.jpg   # Script 2 con una foto, sin cámara
```

Ambas ventanas se cierran presionando cualquier tecla.

## Interfaz en tiempo real (Script 3)

Ventana hecha con `tkinter` (viene con Python) que muestra el video de la cámara en vivo y reconoce las caras cuadro a cuadro:

- Rectángulo verde con el nombre para los mecánicos reconocidos, rojo con "No autorizado" para desconocidos.
- El ingreso se registra solo, tras reconocer a la persona 3 veces seguidas (evita falsos positivos), y una sola vez por día.
- Panel con los ingresos de hoy y el contador de presentes.
- Botón **Agregar mecánico**: toma la cara que ve la cámara y la guarda en `Mecanicos/` con el nombre indicado.
- Botón **Abrir registro (CSV)**.

Nota: el sistema no distingue una persona real de una foto impresa o de una pantalla (para eso haría falta detección de vida).

## Funcionalidades

1. **Carga y procesamiento de imágenes:** lectura de archivos y conversión de BGR a RGB.
2. **Detección y codificación facial:** localiza y codifica los rostros.
3. **Comparación de rostros:** `compare_faces` + `face_distance` para elegir la mejor coincidencia (tolerancia 0.6).
4. **Captura desde cámara web:** toma una imagen en tiempo real.
5. **Registro de asistencia:** guarda nombre, fecha y hora en el CSV; si el mecánico ya ingresó ese día, no duplica el registro.
6. **Visualización gráfica:** rectángulo verde con el nombre para mecánicos reconocidos, rojo con "No autorizado" para desconocidos, y ventanas de control y prueba.

## Cambios respecto a la base

- Temática de taller: carpeta `Mecanicos`, mensajes ("Mecánico verificado", "Persona no autorizada") y archivo `registro_asistencias.csv`.
- Corregido el dibujo del rectángulo en el Script 1 (`cv2.rectangle` recibe dos puntos, no cuatro valores).
- Manejo de errores: foto sin cara, imagen inexistente o cámara que no responde.
- El CSV incluye la fecha y evita duplicados del mismo día; también muestra a las personas no autorizadas.
- La cámara funciona en Windows, Linux y macOS (`CAP_DSHOW` solo en Windows).

## Para personalizarlo

Las fotos de `Mecanicos/` son las de ejemplo de la base. Reemplazalas por fotos frontales y bien iluminadas del personal real, con el nombre del archivo como nombre de la persona (por ejemplo `Carlos Gómez.jpg`).
