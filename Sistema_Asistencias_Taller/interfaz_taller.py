"""
TALLER MECANICO - Interfaz grafica con reconocimiento facial en TIEMPO REAL (Script 3)

Muestra el video de la camara web en vivo, reconoce a los mecanicos cuadro a
cuadro y registra su ingreso automaticamente en el CSV. Reutiliza las funciones
de asistencia_taller.py (carga de la base de datos, codificacion y registro).

Uso:
    python interfaz_taller.py
"""
import csv                                # Importa módulo para leer/escribir archivos .csv
import math                               # Importa funciones matemáticas (usado para dibujar el logo circular)
import os                                 # Importa utilidades del sistema operativo (rutas, archivos)
import subprocess                         # Importa módulo para ejecutar programas externos (abrir el Excel/CSV)
import sys                                # Importa módulo para detectar en qué sistema operativo estamos (Windows/Mac/Linux)
import tkinter as tk                      # Importa la librería gráfica principal y la apoda 'tk'
import unicodedata                        # Importa módulo para limpiar textos (quitar tildes y acentos)
from datetime import datetime             # Importa la herramienta para obtener la fecha y la hora actual
from functools import lru_cache           # Importa decorador para guardar resultados en memoria caché y acelerar el programa
from tkinter import messagebox, simpledialog, ttk  # Importa alertas, pop-ups de texto y widgets modernos de tabla (ttk)

import cv2                                # Importa OpenCV, la librería encargada de manejar la cámara web
import face_recognition as fr             # Importa la Inteligencia Artificial que detecta y compara rostros
import numpy                              # Importa librería matemática de alto rendimiento para calcular distancias entre rostros
from PIL import Image, ImageDraw, ImageFont, ImageTk # Importa Pillow para dibujar gráficos bonitos encima del video

# Importa variables y funciones desde tu otro archivo "asistencia_taller.py"
from asistencia_taller import (ARCHIVO_REGISTRO, RUTA_MECANICOS, TOLERANCIA,
                               cargar_mecanicos, codificar, registrar_ingreso)

# --- Configuracion -----------------------------------------------------------

ESCALA = 0.5              # Define a qué tamaño se reduce el video para procesarlo (0.5 = 50% de su tamaño original)
CADA_N_CUADROS = 3        # Indica que la IA solo procesará 1 de cada 3 fotogramas (ahorra CPU)
CONFIRMACIONES = 3        # Número de veces seguidas que la IA debe ver una cara para confirmar el ingreso
ANCHO, ALTO = 640, 480    # Resolución predeterminada que se le pedirá a la cámara web
ANCHO_MAX = 800           # Límite máximo de ancho del recuadro por si la cámara manda más resolución

# --- Paleta (tema oscuro, acento naranja taller) -----------------------------

FONDO = "#0e1013"         # Color hexadecimal del fondo principal de la aplicación (gris casi negro)
BARRA = "#0a0c0f"         # Color hexadecimal para la barra inferior de estado (un poco más oscuro)
TARJETA = "#1a1d23"       # Color hexadecimal para el fondo de los recuadros de la derecha
FILA_ALT = "#20242b"      # Color hexadecimal para intercalar el fondo de las filas de la tabla
BORDE = "#2a2f38"         # Color hexadecimal para las líneas de separación y bordes
NARANJA = "#ff7a00"       # Color principal de la marca del taller (naranja vibrante)
NARANJA_HOVER = "#e06a00" # Color naranja más oscuro para cuando el mouse pasa por arriba del botón
TEXTO = "#e8eaed"         # Color blanco-grisáceo para que el texto principal no canse la vista
GRIS = "#8b93a1"          # Color gris apagado para textos secundarios y subtítulos
VERDE = "#22c55e"         # Color verde para indicar éxito o ingreso correcto
ROJO = "#ef4444"          # Color rojo para indicar alertas, errores o personas desconocidas
AZUL = "#3b82f6"          # Color azul para el estado inicial de "Esperando"
FUENTE = "Segoe UI"       # Nombre de la tipografía que se usará en toda la interfaz gráfica


# --- Utilidades de dibujo ----------------------------------------------------

def sin_tildes(texto):
    """Solo se usa si no hay una fuente TrueType disponible (la de OpenCV no dibuja tildes)."""
    # Separa las letras de sus signos ortográficos (ej: 'á' se vuelve 'a' + '´')
    normal = unicodedata.normalize('NFKD', texto)
    # Reconstruye el texto ignorando los signos ortográficos (las tildes)
    return ''.join(c for c in normal if not unicodedata.combining(c))


@lru_cache(maxsize=16)    # Guarda en memoria las últimas 16 veces que se llamó a esta función para no leer el disco a cada rato
def cargar_fuente(tamano, negrita=True):
    """Busca una fuente TrueType del sistema (Segoe UI en Windows) con soporte de tildes."""
    if negrita:           # Si se pide la fuente en negrita (bold)
        # Lista de archivos de fuentes en negrita comunes en distintos sistemas operativos
        nombres = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]
    else:                 # Si se pide la fuente normal (regular)
        # Lista de archivos de fuentes normales
        nombres = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Arial.ttf"]
        
    for nombre in nombres: # Recorre la lista de nombres uno por uno
        try:
            # Intenta cargar la fuente desde el sistema con el tamaño indicado
            return ImageFont.truetype(nombre, tamano)
        except OSError:    # Si esa fuente no existe en la PC, salta el error y...
            continue       # ...pasa al siguiente nombre de la lista
            
    try:                   # Si no encontró ninguna de las fuentes anteriores
        return ImageFont.load_default(tamano) # Intenta cargar la fuente básica por defecto con tamaño
    except TypeError:      # Si la versión de Pillow es vieja y no acepta tamaño por defecto
        return ImageFont.load_default()       # Carga la fuente por defecto sin tamaño específico


def texto_seguro(texto, fuente):
    # Si la fuente resultó ser la básica (que no soporta tildes y tira error), le borramos las tildes al texto. Si es normal, lo dejamos tal cual.
    return sin_tildes(texto) if isinstance(fuente, ImageFont.ImageFont) else texto


def escribir(d, xy, texto, fuente, color, anchor="lm"):
    # Prepara el texto asegurándose de que no tenga tildes si la fuente no lo soporta
    texto = texto_seguro(texto, fuente)
    try:
        # Intenta dibujar el texto en las coordenadas 'xy' usando el anclaje 'anchor' (ej: centrado)
        d.text(xy, texto, font=fuente, fill=color, anchor=anchor)
    except ValueError:     # Si la fuente es básica y no sabe lo que es 'anchor', tira ValueError
        # Lo dibuja de la forma antigua sin anclaje, restándole 6px a 'y' para acomodarlo a ojo
        d.text((xy[0], xy[1] - 6), texto, font=fuente, fill=color)


def dibujar_esquinas(d, caja, color, grosor=3):
    """Marco de reconocimiento: solo las cuatro esquinas, como un visor profesional."""
    # Extrae las coordenadas X e Y de las esquinas superior-izquierda e inferior-derecha de la cara
    x1, y1, x2, y2 = caja
    # Calcula el largo de los palitos: será 1/4 del tamaño de la cara, con un mínimo de 14 píxeles
    largo = max(14, min(x2 - x1, y2 - y1) // 4)
    
    # Recorre 4 grupos de coordenadas para dibujar las 4 esquinas. (px,py)=punto origen, (dx,dy)=dirección
    for px, py, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        # Dibuja el palito horizontal de la esquina actual
        d.line([(px, py), (px + dx * largo, py)], fill=color, width=grosor)
        # Dibuja el palito vertical de la esquina actual
        d.line([(px, py), (px, py + dy * largo)], fill=color, width=grosor)


def generar_placeholder(ancho, alto):
    """Imagen que se muestra mientras la camara esta apagada."""
    # Crea una imagen completamente nueva en formato RGB con el color de FONDO de la app
    img = Image.new("RGB", (ancho, alto), FONDO)
    # Instancia la herramienta de dibujo sobre esta imagen nueva
    d = ImageDraw.Draw(img)
    
    # Bucle que va desde 0 hasta el ancho de la imagen, saltando de a 40 píxeles
    for x in range(0, ancho, 40):
        # Dibuja una línea vertical oscura para simular una grilla de diseño
        d.line([(x, 0), (x, alto)], fill="#13161b")
        
    # Bucle que va desde 0 hasta el alto de la imagen, saltando de a 40 píxeles
    for y in range(0, alto, 40):
        # Dibuja una línea horizontal oscura para completar la grilla
        d.line([(0, y), (ancho, y)], fill="#13161b")

    # Encuentra la mitad del ancho (cx) y la mitad del alto menos 36 píxeles (cy) para centrar el icono
    cx, cy = ancho // 2, alto // 2 - 36
    
    # Dibuja el rectángulo principal de la cámara con bordes curvos (radius=12) y trazo ancho
    d.rounded_rectangle((cx - 50, cy - 28, cx + 50, cy + 34), radius=12, outline=GRIS, width=4)
    # Dibuja un rectángulo arriba simulando el flash o disparador de la cámara
    d.rectangle((cx - 20, cy - 40, cx + 20, cy - 28), outline=GRIS, width=4)
    # Dibuja un círculo naranja en el medio simulando la lente
    d.ellipse((cx - 22, cy - 12, cx + 22, cy + 30), outline=NARANJA, width=4)

    # Escribe el texto grande "Cámara apagada" debajo del icono, centrado ("mm")
    escribir(d, (cx, cy + 82), "Cámara apagada", cargar_fuente(24), TEXTO, "mm")
    # Escribe el texto pequeño de ayuda debajo del texto grande, centrado ("mm")
    escribir(d, (cx, cy + 116), "Presioná «Iniciar cámara» para comenzar", cargar_fuente(15, False), GRIS, "mm")
    
    return img  # Devuelve la imagen de "Cámara apagada" lista para usar


# --- Reconocimiento ----------------------------------------------------------

class Reconocedor:
    """Base de datos de mecanicos y reconocimiento de caras en un cuadro de video."""

    def __init__(self):
        # Inicializa una lista vacía para las matemáticas de las caras
        self.codificaciones = []
        # Inicializa una lista vacía para los nombres
        self.nombres = []
        # Ejecuta la función recargar al instanciar la clase
        self.recargar()

    def recargar(self):
        # Llama a cargar_mecanicos (de asistencia_taller) que lee las fotos del disco duro
        imagenes, nombres = cargar_mecanicos(RUTA_MECANICOS)
        # Convierte las fotos en listas de números matemáticos y guarda nombres y códigos
        self.codificaciones, self.nombres = codificar(imagenes, nombres)

    def procesar(self, frame_bgr):
        """Devuelve una lista de (ubicacion, nombre o None, distancia) por cada cara."""
        # Reduce la foto original de la cámara multiplicando su ancho y alto por la ESCALA (ej. 0.5)
        chico = cv2.resize(frame_bgr, (0, 0), fx=ESCALA, fy=ESCALA)
        # Convierte el color de formato BGR (OpenCV) a RGB (el que necesita face_recognition)
        rgb = cv2.cvtColor(chico, cv2.COLOR_BGR2RGB)

        # La IA busca en qué coordenadas de la imagen achicada hay rostros
        ubicaciones = fr.face_locations(rgb)
        # La IA extrae los 128 puntos matemáticos de los rostros encontrados en esas coordenadas
        codificadas = fr.face_encodings(rgb, ubicaciones)

        # Prepara una lista vacía para guardar a los encontrados
        resultados = []
        # El comando 'zip' empareja cada rostro codificado con sus coordenadas (bucle)
        for cara_codif, ubic in zip(codificadas, ubicaciones):
            # Como la imagen estaba achicada, divide las coordenadas por la ESCALA (ej / 0.5) para volver al tamaño original
            ubic_real = tuple(int(v / ESCALA) for v in ubic)
            # Inicializa variables por defecto por si no lo reconoce
            nombre, distancia = None, None

            # Si hay mecánicos en la base de datos (si la lista no está vacía)
            if self.codificaciones:
                # Compara la cara del video con TODAS las de la base de datos. Devuelve una lista de diferencias (distancias)
                distancias = fr.face_distance(self.codificaciones, cara_codif)
                # Encuentra el índice (posición en la lista) de la cara que tuvo la menor diferencia (más parecida)
                indice = int(numpy.argmin(distancias))
                # Extrae ese número de distancia ganadora
                distancia = float(distancias[indice])
                
                # Si la diferencia es menor al límite de TOLERANCIA aceptado...
                if distancia <= TOLERANCIA:
                    # Lo da por reconocido y guarda el nombre correspondiente a ese índice
                    nombre = self.nombres[indice]

            # Agrega los datos finales a la lista (dónde está, cómo se llama, qué tan parecido es)
            resultados.append((ubic_real, nombre, distancia))
            
        return resultados # Devuelve la lista completa de resultados al programa


# --- Registro del dia --------------------------------------------------------

def leer_registrados_hoy():
    """Devuelve {nombre: hora} de los ingresos de hoy segun el CSV."""
    # Saca la fecha de hoy en formato Día/Mes/Año
    hoy = datetime.now().strftime('%d/%m/%Y')
    # Prepara un diccionario vacío
    registrados = {}
    
    # Comprueba si el archivo CSV ya existe físicamente en la computadora
    if os.path.isfile(ARCHIVO_REGISTRO):
        # Lo abre en modo lectura ('r' implícito) con codificación para acentos (utf-8)
        with open(ARCHIVO_REGISTRO, newline='', encoding='utf-8') as f:
            # Lo lee como un diccionario donde la fila 1 son las claves
            for fila in csv.DictReader(f):
                # Si la celda 'fecha' de esta fila es exactamente igual a la fecha de hoy
                if fila.get('fecha') == hoy:
                    # Crea una clave con el nombre del mecánico y le asigna su hora de ingreso
                    registrados[fila['nombre']] = fila['hora_ingreso']
                    
    return registrados # Retorna el diccionario listo


# --- Widgets -----------------------------------------------------------------

class Boton(tk.Label):
    """Boton plano con efecto al pasar el mouse."""

    def __init__(self, padre, texto, color, hover, comando, borde=None):
        # Hereda las propiedades de tk.Label (crea una etiqueta que usaremos como botón)
        super().__init__(padre, text=texto, bg=color, fg="white",
                         font=(FUENTE, 11, "bold"), pady=11, cursor="hand2", # cursor de manito
                         highlightthickness=1, highlightbackground=borde or color) # Borde personalizado
                         
        # Guarda el color original, el color de paso del mouse (hover) y la función a ejecutar
        self.color, self.hover, self.comando = color, hover, comando
        
        # Le enseña al botón qué hacer cuando el mouse entra al área: pinta del color 'hover'
        self.bind("<Enter>", lambda e: self.configure(bg=self.hover))
        # Le enseña al botón qué hacer cuando el mouse sale: vuelve a pintar del color original
        self.bind("<Leave>", lambda e: self.configure(bg=self.color))
        # Le enseña al botón qué hacer al recibir un clic izquierdo: ejecuta la función 'comando'
        self.bind("<Button-1>", lambda e: self.comando())

    def cambiar(self, texto, color, hover):
        # Función auxiliar para mutar el botón (ej: transformarlo de verde a rojo)
        self.color, self.hover = color, hover
        # Actualiza su texto, fondo y color de borde
        self.configure(text=texto, bg=color, highlightbackground=color)


# --- Aplicación --------------------------------------------------------------

class App(tk.Tk):
    # Constructor de la ventana principal de la aplicación
    def __init__(self):
        super().__init__()        # Inicializa tk.Tk() para crear la ventana madre
        self.title("Taller Mecánico · Control de Asistencia") # Título de la ventana en la barra
        self.configure(bg=FONDO)  # Pinta el fondo principal del color negro/gris
        self.resizable(False, False) # Desactiva el botón de maximizar y estirar ventana

        # Variables de estado y lógica interna
        self.reconocedor = Reconocedor() # Crea el "cerebro" instanciando la clase Reconocedor
        self.captura = None           # Variable que guardará la conexión a la cámara web
        self.corriendo = False        # Bandera lógica para saber si el video se está reproduciendo
        self.tam_video = (ANCHO, ALTO)# Resolución actual que ocupará el recuadro negro del video
        self.contador_cuadros = 0     # Contador infinito de cuántas fotos procesó la cámara
        self.cuadros_seg = 0          # Contador que se resetea por segundo para medir los FPS
        self.ultimos = []             # Almacena las coordenadas de las caras detectadas en el último cuadro
        self.confirmaciones = {}      # Diccionario para contar cuántas veces se vio a una misma persona {nombre: contador}
        self.ultimo_cuadro = None     # Foto "cruda" guardada en RAM por si tocan el botón "Añadir mecánico"
        self.imagen_tk = None         # Objeto final de la imagen preparada para que Tkinter la pinte
        self._estado_actual = None    # Control para evitar redibujar el panel de estado si el texto es el mismo
        self.registrados_hoy = leer_registrados_hoy() # Llama la función para leer los presentes de hoy

        self.configurar_estilos()     # Llama al método que configura colores de la tabla
        self.construir_interfaz()     # Llama al método gigantesco que arma la grilla de pantalla
        
        self.lbl_camara.configure(text="Cámara apagada") # Escribe el estado en la barra inferior
        self.mostrar_placeholder()    # Dibuja la foto falsa de la camarita en el espacio vacío
        self.actualizar_tabla()       # Dibuja los mecánicos leídos del CSV en la tabla de Tkinter
        # Define el cartelote lateral de estado en CÁMARA APAGADA
        self.estado("CÁMARA APAGADA", "Presioná «Iniciar cámara» para comenzar", GRIS, BORDE)
        
        self.tick()                   # Llama por primera vez al reloj para que empiece el ciclo infinito de tiempo
        self.centrar()                # Corre la función que mueve la ventana al medio del monitor
        self.protocol("WM_DELETE_WINDOW", self.cerrar) # Le avisa a Windows qué función correr si tocan la 'X' roja

    # ---- Construccion de la ventana ------------------------------------------
    
    def configurar_estilos(self):
        # Accede a las propiedades visuales avanzadas de Tkinter
        estilo = ttk.Style(self)
        estilo.theme_use("clam")  # Usa un tema base sin relieves molestos de los años 90
        # Elimina un borde blanco fantasma que Treeview pone por defecto
        estilo.layout("Taller.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        
        # Configura fondo, texto y filas de la tabla principal
        estilo.configure("Taller.Treeview", background=TARJETA, fieldbackground=TARJETA,
                         foreground=TEXTO, rowheight=30, borderwidth=0, font=(FUENTE, 11))
        # Configura el encabezado (título de columnas) de la tabla
        estilo.configure("Taller.Treeview.Heading", background=BORDE, foreground=GRIS,
                         relief="flat", borderwidth=0, font=(FUENTE, 9, "bold"), padding=(8, 6))
        # Anula colores molestos cuando el mouse pasa por encima del título de columna
        estilo.map("Taller.Treeview.Heading", background=[("active", BORDE)])
        # Configura colores cuando haces clic/seleccionas a alguien en la tabla (lo disimula dejándolo igual)
        estilo.map("Taller.Treeview", background=[("selected", TARJETA)],
                   foreground=[("selected", TEXTO)])

    def tarjeta(self, padre):
        # Devuelve un contenedor con fondo color TARJETA y un pequeño contorno del color BORDE
        return tk.Frame(padre, bg=TARJETA, highlightbackground=BORDE, highlightthickness=1)

    def construir_interfaz(self):
        # Permite que la columna 0 del grid principal se expanda si sobra espacio
        self.grid_columnconfigure(0, weight=1)

        # -- Encabezado ------------------------------------
        
        cab = tk.Frame(self, bg=TARJETA) # Crea un panel superior para el título
        cab.grid(row=0, column=0, columnspan=2, sticky="ew") # Ocupa fila 0, de izquierda a derecha (ew)

        # Crea un lienzo (Canvas) de 52x52 para dibujar un logo personalizado
        logo = tk.Canvas(cab, width=52, height=52, bg=TARJETA, highlightthickness=0)
        logo.pack(side="left", padx=(20, 12), pady=12)
        cx = cy = 26              # Coordenadas centrales del lienzo 52x52
        for i in range(8):        # Bucle para dibujar 8 engranajes
            a = math.radians(i * 45) # Ángulo rotando 45 grados por diente
            # Tira una línea gruesa desde el centro hacia afuera
            logo.create_line(cx + 13 * math.cos(a), cy + 13 * math.sin(a),
                             cx + 23 * math.cos(a), cy + 23 * math.sin(a),
                             fill=NARANJA, width=7)
        # Tapa las líneas dibujando un óvalo grande naranja encima, creando un anillo
        logo.create_oval(cx - 17, cy - 17, cx + 17, cy + 17, fill=NARANJA, outline=NARANJA)
        # Tapa el centro del anillo dibujando un óvalo del color de fondo, creando el hueco del engranaje
        logo.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=TARJETA, outline=TARJETA)

        # Panel agrupará el título y subtítulo a la derecha del logo
        titulos = tk.Frame(cab, bg=TARJETA)
        titulos.pack(side="left")
        # Título grande
        tk.Label(titulos, text="TALLER MECÁNICO", bg=TARJETA, fg=TEXTO,
                 font=(FUENTE, 17, "bold")).pack(anchor="w") # "w" ancla el texto al Oeste (izquierda)
        # Subtítulo chico
        tk.Label(titulos, text="Control de asistencia  ·  Reconocimiento facial",
                 bg=TARJETA, fg=GRIS, font=(FUENTE, 10)).pack(anchor="w")

        # Panel que agrupará la hora y la fecha, colocado del lado derecho de la pantalla
        reloj = tk.Frame(cab, bg=TARJETA)
        reloj.pack(side="right", padx=22)
        # Etiqueta que guardará la hora (números grandes)
        self.lbl_hora = tk.Label(reloj, bg=TARJETA, fg=TEXTO, font=(FUENTE, 22, "bold"))
        self.lbl_hora.pack(anchor="e") # "e" ancla al Este (derecha)
        # Etiqueta que guardará la fecha
        self.lbl_fecha = tk.Label(reloj, bg=TARJETA, fg=GRIS, font=(FUENTE, 10))
        self.lbl_fecha.pack(anchor="e")

        # Dibuja una línea de 3 pixeles color naranja que cruza toda la pantalla separando el encabezado del cuerpo
        tk.Frame(self, bg=NARANJA, height=3).grid(row=1, column=0, columnspan=2, sticky="ew")

        # -- Video en vivo (Panel de la izquierda)
        izq = tk.Frame(self, bg=FONDO)
        izq.grid(row=2, column=0, padx=(20, 10), pady=20, sticky="n") # Ubicado en fila 2, columna 0, anclado al Norte
        # Marco sutil que rodea al video y que cambia de color rojo/verde según quién pasa
        self.marco_borde = tk.Frame(izq, bg=BORDE, padx=3, pady=3)
        self.marco_borde.pack()
        # Contenedor del video con tamaño forzado a 640x480
        self.marco_video = tk.Frame(self.marco_borde, bg="black", width=ANCHO, height=ALTO)
        self.marco_video.pack_propagate(False)       # Prohíbe que el Frame cambie de tamaño, lo bloquea.
        self.marco_video.pack()
        # Etiqueta vacía donde el bucle irá inyectando los fotogramas (imágenes) de la webcam
        self.lbl_video = tk.Label(self.marco_video, bg="black", bd=0)
        self.lbl_video.pack(fill="both", expand=True)

        # Tarjeta horizontal debajo del video que explica qué es cada color
        leyenda = self.tarjeta(izq)
        leyenda.pack(fill="x", pady=(14, 0))
        # Recorre 3 colores y 3 textos para crear los circulitos indicadores
        for color, texto in ((VERDE, "Mecánico reconocido"), (ROJO, "Persona no autorizada"),
                             (AZUL, "Esperando persona")):
            item = tk.Frame(leyenda, bg=TARJETA)
            item.pack(side="left", expand=True, pady=14)
            # Lienzo chiquito de 12x12 para el círculo
            punto = tk.Canvas(item, width=12, height=12, bg=TARJETA, highlightthickness=0)
            punto.create_oval(1, 1, 11, 11, fill=color, outline=color) # Dibuja el círculo
            punto.pack(side="left", padx=(0, 7))
            # Pone la explicación al lado del círculo
            tk.Label(item, text=texto, bg=TARJETA, fg=GRIS, font=(FUENTE, 10)).pack(side="left")

        # -- Panel derecho (Estados y Tabla) ---------------------------------
        
        der = tk.Frame(self, bg=FONDO)
        der.grid(row=2, column=1, padx=(10, 20), pady=20, sticky="ns") # Fila 2, columna 1, se estira Norte-Sur

        # Tarjeta 1: Recuadro que muestra a quién detectó
        c1 = self.tarjeta(der)
        c1.pack(fill="x") # Se estira horizontalmente
        # Franja decorativa gruesa a la izquierda que cambia de color rojo/verde/azul
        self.franja = tk.Frame(c1, bg=GRIS, width=5)
        self.franja.pack(side="left", fill="y")
        # Contenedor del contenido del recuadro
        cuerpo = tk.Frame(c1, bg=TARJETA)
        cuerpo.pack(side="left", fill="both", expand=True)
        tk.Label(cuerpo, text="ESTADO", bg=TARJETA, fg=GRIS,
                 font=(FUENTE, 9, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
        # Aquí se mostrará por ejemplo "INGRESO REGISTRADO"
        self.lbl_titulo = tk.Label(cuerpo, bg=TARJETA, fg=GRIS, anchor="w",
                                   font=(FUENTE, 17, "bold"))
        self.lbl_titulo.pack(fill="x", padx=16)
        # Aquí se mostrará "Juan Pérez - 08:30"
        self.lbl_detalle = tk.Label(cuerpo, bg=TARJETA, fg=TEXTO, anchor="w",
                                    justify="left", wraplength=290, height=2, font=(FUENTE, 10))
        self.lbl_detalle.pack(fill="x", padx=16, pady=(0, 14))

        # Tarjeta 2: Recuadro que contiene los presentes del día
        c2 = self.tarjeta(der)
        c2.pack(fill="both", expand=True, pady=(14, 0))
        tk.Label(c2, text="ASISTENCIA DE HOY", bg=TARJETA, fg=GRIS,
                 font=(FUENTE, 9, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
        
        # Agrupa el contador de mecánicos (ej: "3") y su explicación (ej: "de 10 presentes")
        fila = tk.Frame(c2, bg=TARJETA)
        fila.pack(fill="x", padx=16)
        self.lbl_num = tk.Label(fila, bg=TARJETA, fg=TEXTO, font=(FUENTE, 26, "bold"))
        self.lbl_num.pack(side="left")
        self.lbl_num_txt = tk.Label(fila, bg=TARJETA, fg=GRIS, font=(FUENTE, 10))
        self.lbl_num_txt.pack(side="left", padx=(8, 0), pady=(10, 0))
        
        # Lienzo largo que usaremos para dibujar la barra verde de progreso
        self.barra = tk.Canvas(c2, width=296, height=8, bg=TARJETA, highlightthickness=0)
        self.barra.pack(padx=16, pady=(2, 12))

        # Inicializa la tabla Treeview para mostrar el listado de personas
        self.tabla = ttk.Treeview(c2, columns=("mecanico", "hora"), show="headings",
                                  style="Taller.Treeview", height=5, selectmode="none")
        self.tabla.heading("mecanico", text="MECÁNICO", anchor="w") # Título de columna 1
        self.tabla.heading("hora", text="INGRESO", anchor="w")      # Título de columna 2
        self.tabla.column("mecanico", width=190, anchor="w")        # Ancho columna 1
        self.tabla.column("hora", width=106, anchor="w")            # Ancho columna 2
        # Configura "tags" para poder asignar colores a filas específicas desde el código
        self.tabla.tag_configure("par", background=TARJETA)
        self.tabla.tag_configure("impar", background=FILA_ALT)
        self.tabla.tag_configure("vacio", foreground=GRIS)
        self.tabla.pack(padx=16, pady=(0, 16)) # Ubica la tabla en la tarjeta

        # Instancia los botones usando la clase personalizada "Boton" que programamos arriba
        self.btn_camara = Boton(der, "Iniciar cámara", NARANJA, NARANJA_HOVER, self.alternar_camara)
        self.btn_camara.pack(fill="x", pady=(14, 0))
        
        Boton(der, "Agregar mecánico", TARJETA, BORDE, self.agregar_mecanico,
              borde=BORDE).pack(fill="x", pady=(8, 0))
              
        Boton(der, "Abrir registro (CSV)", TARJETA, BORDE, self.abrir_registro,
              borde=BORDE).pack(fill="x", pady=(8, 0))

        # -- Barra de estado inferior (Status bar) ------------------------------
        
        tk.Frame(self, bg=BORDE, height=1).grid(row=3, column=0, columnspan=2, sticky="ew") # Línea divisoria finita
        barra = tk.Frame(self, bg=BARRA)      # Frame muy oscuro para el pie de programa
        barra.grid(row=4, column=0, columnspan=2, sticky="ew")
        
        # Punto circular que indicará si la cámara envía señal
        self.punto = tk.Canvas(barra, width=14, height=14, bg=BARRA, highlightthickness=0)
        self.punto.pack(side="left", padx=(20, 6), pady=8)
        # id_punto guarda el "ID" del dibujo para poder repintarlo después
        self.id_punto = self.punto.create_oval(2, 2, 12, 12, fill=GRIS, outline=GRIS)
        
        # Etiqueta que dirá "Cámara apagada" o "activa"
        self.lbl_camara = tk.Label(barra, bg=BARRA, fg=GRIS, font=(FUENTE, 9))
        self.lbl_camara.pack(side="left")
        # Etiqueta que dirá "30 FPS" a la derecha
        self.lbl_fps = tk.Label(barra, bg=BARRA, fg=GRIS, font=(FUENTE, 9))
        self.lbl_fps.pack(side="right", padx=20)
        # Etiqueta que avisa a cuánta gente leyó en la carpeta de fotos
        self.lbl_base = tk.Label(barra, bg=BARRA, fg=GRIS, font=(FUENTE, 9))
        self.lbl_base.pack(side="right", padx=(0, 16))

    def centrar(self):
        # update_idletasks obliga a la compu a procesar y dibujar las interfaces pendientes
        # Es necesario para saber el ancho/alto de la ventana antes de centrarla
        self.update_idletasks()
        # Calcula el Punto X: (Ancho total del monitor - Ancho del programa) dividido a la mitad
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        # Calcula el Punto Y de la misma forma, restándole 20px para que quede un poco más alto
        y = max(0, (self.winfo_screenheight() - self.winfo_height()) // 2 - 20)
        # Le inyecta esas nuevas coordenadas de posición a la ventana
        self.geometry(f"+{x}+{y}")

    # ---- Reloj, FPS y datos del panel ---------------------------------------
    
    def tick(self):
        # Esta función es un bucle infinito separado que corre cada 1 segundo
        ahora = datetime.now() # Captura qué hora es
        # Convierte la hora a cadena (ej "14:35:10") y actualiza el label
        self.lbl_hora.configure(text=ahora.strftime('%H:%M:%S'))
        # Convierte la fecha y actualiza
        self.lbl_fecha.configure(text=ahora.strftime('%d/%m/%Y'))
        # Si la cámara anda, pega los cuadros del segundo que acaba de pasar. Si no, pega guiones.
        self.lbl_fps.configure(text=f"{self.cuadros_seg} FPS" if self.corriendo else "— FPS")
        # Resetea a cero los cuadros de cámara leídos porque empieza un segundo nuevo
        self.cuadros_seg = 0
        # self.after es de Tkinter: "Llama a self.tick dentro de 1000 milisegundos (1 segundo)"
        self.after(1000, self.tick)

    def actualizar_tabla(self):
        # Borra todos los ítems actuales del componente Treeview usando un unpack de tupla (*)
        self.tabla.delete(*self.tabla.get_children())
        
        # Si el diccionario de ingresos está vacío...
        if not self.registrados_hoy:
            # Mete un texto gris diciendo que no hay ingresos
            self.tabla.insert("", "end", values=("Sin ingresos todavía", ""), tags=("vacio",))
            
        # Ordena el diccionario según la hora (x[1]) y recorre (índice, nombre, hora)
        for i, (nombre, hora) in enumerate(sorted(self.registrados_hoy.items(),
                                                  key=lambda x: x[1])):
            # Mete una nueva fila al Treeview. Si el índice 'i' es par (ej 0, 2, 4) le asigna tag "par"
            # Si es impar, le asigna tag "impar", logrando que las filas alternen colores
            self.tabla.insert("", "end", values=(nombre, hora),
                              tags=("par" if i % 2 == 0 else "impar",))

        # Calcula cuanta gente hay en la base vs gente presente en CSV
        total = len(self.reconocedor.nombres)
        presentes = len(self.registrados_hoy)
        
        # Modifica el número enorme y el texto chiquito
        self.lbl_num.configure(text=str(presentes))
        self.lbl_num_txt.configure(text=f"de {total} mecánicos presentes")
        # Actualiza la etiqueta pequeña de abajo a la derecha
        self.lbl_base.configure(text=f"Base de datos: {total} mecánicos")

        # -- Barra de Progreso Visual --
        self.barra.delete("all") # Borra dibujos viejos del lienzo
        # Dibuja la pista gris del fondo de la barra de 296 pixeles de ancho
        self.barra.create_rectangle(0, 0, 296, 8, fill=BORDE, outline=BORDE)
        
        if total: # Si al menos hay 1 mecánico en la base
            # Calculamos ancho verde (regla de 3 simple). min(presentes, total) previene que se desborde el 100%
            ancho = int(296 * min(presentes, total) / total)
            if ancho: # Si el ancho es mayor a 0
                # Dibuja un rectángulo verde superpuesto con el tamaño calculado
                self.barra.create_rectangle(0, 0, ancho, 8, fill=VERDE, outline=VERDE)

    def estado(self, titulo, detalle, color, borde=None):
        # Esta función muta todos los colores y textos del cartel lateral a la vez
        # Armamos una "huella" o clave para saber si lo que se va a imprimir es igual a lo que ya está
        clave = (titulo, detalle, color, borde)
        if clave == self._estado_actual:
            return # Si es igual, aborta. Esto evita sobrecargar a Tkinter repintando cosas que ya están iguales
        self._estado_actual = clave # Si es distinto, guarda esta nueva clave
        
        # Reemplaza los colores y títulos
        self.lbl_titulo.configure(text=titulo, fg=color)
        self.lbl_detalle.configure(text=detalle)
        self.franja.configure(bg=color)
        # El marco del video se pinta del color que pidas, y si no pides borde, del mismo color del texto
        self.marco_borde.configure(bg=borde or color)

    def sonido(self):
        # Intenta reproducir el sonido predeterminado de acierto si estamos en Windows
        if sys.platform.startswith('win'):
            try:
                import winsound
                # Reproduce un 'ding' de sistema de forma asincrónica (para no trabar el programa mientras suena)
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass # Si el equipo no tiene altavoces o tira error, no hace nada

    # ---- Cámara ---------------------------------
    
    def abrir_camara(self):
        # Intenta prender la cámara conectada en puerto USB 0, luego la 1 y luego la 2
        for indice in range(3):
            # En Windows (win) usamos CAP_DSHOW de OpenCV porque arranca instantáneo (DirectShow)
            if sys.platform.startswith('win'):
                captura = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
            else:
                captura = cv2.VideoCapture(indice) # En Linux/Mac lo arranca normal
                
            # isOpened() es un método de cv2 que dice True si la luz de la camarita prendió
            if captura.isOpened():
                # Forzamos la resolución al objeto cámara 
                captura.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
                captura.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
                # Retorna el objeto listo para usar, saliendo de la función
                return captura
                
            # Si esa cámara no anduvo, la desconecta bien antes de probar el siguiente índice de USB
            captura.release()
        return None # Si el bucle termina y nada anduvo, retorna None

    def ajustar_video(self, ancho, alto):
        """Si la webcam tira otra resolución (ej: 1920x1080) lo achica sin deformarlo para Tkinter."""
        # Saca qué tan grande es la imagen respecto al máximo permitido
        escala = min(1.0, ANCHO_MAX / ancho)
        # Aplica esa escala y lo guarda en self.tam_video
        self.tam_video = (int(ancho * escala), int(alto * escala))
        # Ajusta el Frame de Tkinter para que envuelva la nueva resolución
        self.marco_video.configure(width=self.tam_video[0], height=self.tam_video[1])

    def alternar_camara(self):
        # Función "router" conectada al botón naranja.
        if self.corriendo:
            self.detener() # Si la bandera era True, va y apaga
        else:
            self.iniciar() # Si la bandera era False, va y prende

    def iniciar(self):
        if self.corriendo: # Chequeo extra de seguridad
            return
            
        # Llama a abrir_camara y guarda el objeto de conexión
        self.captura = self.abrir_camara()
        
        # Si fue None, significa que no detectó cámara en ningún USB
        if self.captura is None:
            # Muestra el popup de error al usuario
            messagebox.showerror("Cámara", "No se pudo abrir la cámara.\n"
                                 "Verificá que esté conectada y que ninguna otra "
                                 "aplicación la esté usando.")
            return

        # Saca una fotito de prueba (.read) para ver qué resolución nos entregó el hardware
        exito, cuadro = self.captura.read()
        if exito:
            # Le pasa el ancho (.shape[1]) y alto (.shape[0]) a la función para ajustar Tkinter
            self.ajustar_video(cuadro.shape[1], cuadro.shape[0])

        self.corriendo = True # Cambia el estado a activo
        
        # Llama al método "cambiar" del botón para que ahora sea Rojo y diga "Detener cámara"
        self.btn_camara.cambiar("Detener cámara", ROJO, "#d83a3a")
        # Pinta de verde el circulito chiquito del pie del programa
        self.punto.itemconfigure(self.id_punto, fill=VERDE, outline=VERDE)
        # Cambia el texto del pie a blanco y pone "Activa"
        self.lbl_camara.configure(text="Cámara activa", fg=TEXTO)
        # Cambia el cartel gigante a color AZUL (Esperando)
        self.estado("ESPERANDO", "Acercate a la cámara para registrar tu ingreso", AZUL, BORDE)
        
        # Llama a la función reina, la que entra en un loop infinito de procesamiento
        self.bucle()

    def detener(self):
        # Baja la bandera de ejecución
        self.corriendo = False
        
        if self.captura is not None:
            # .release() desvincula el hardware de la webcam para que la luz se apague
            self.captura.release()
            self.captura = None
            
        # Borra historiales de reconocimientos a medias
        self.ultimos = []
        self.confirmaciones = {}
        
        # Vuelve el botón a estado naranja original
        self.btn_camara.cambiar("Iniciar cámara", NARANJA, NARANJA_HOVER)
        # Vuelve el circulito a gris
        self.punto.itemconfigure(self.id_punto, fill=GRIS, outline=GRIS)
        self.lbl_camara.configure(text="Cámara apagada", fg=GRIS)
        
        # Dibuja la foto del diseño gris falso en lugar del recuadro negro
        self.mostrar_placeholder()
        # Vuelve el cartelón principal a estado gris y lo avisa
        self.estado("CÁMARA APAGADA", "Presioná «Iniciar cámara» para comenzar", GRIS, BORDE)

    def mostrar_placeholder(self):
        # Llama a la función que dibuja el diseño gris de la cámara
        # *self.tam_video desempaqueta la tupla para mandar el ancho y el alto a la función
        # Convierte esa imagen dibujada a formato PhotoImage de Tkinter
        self.imagen_tk = ImageTk.PhotoImage(generar_placeholder(*self.tam_video))
        # Pega esa imagen en la etiqueta que simula ser un monitor
        self.lbl_video.configure(image=self.imagen_tk)

    # ---- Bucle de video en tiempo real --------------------------
    
    def bucle(self):
        # Si se tocó "Detener", la bandera bajó, y este 'return' rompe el ciclo infinito
        if not self.corriendo:
            return

        # Saca una captura en vivo (.read() devuelve el estado de éxito y la matriz matemática de la imagen)
        exito, cuadro = self.captura.read()
        if exito: # Si la imagen llegó bien y no se corrompió el USB
            # cv2.flip lo gira horizontalmente. Sin esto el usuario se ve a la inversa y es mareante
            cuadro = cv2.flip(cuadro, 1)
            
            # Si la webcam mandó un tamaño distinto al que habíamos pactado, lo forzamos a redimensionarse
            if (cuadro.shape[1], cuadro.shape[0]) != self.tam_video:
                cuadro = cv2.resize(cuadro, self.tam_video)
                
            # Guardamos una copia idéntica del cuadro (sin rectángulos dibujados) en RAM
            self.ultimo_cuadro = cuadro.copy()
            # Le sumamos 1 foto al contador histórico
            self.contador_cuadros += 1
            # Le sumamos 1 foto al contador del segundo (para saber los FPS)
            self.cuadros_seg += 1

            # LA MAGIA DE LA OPTIMIZACIÓN:
            # Solo si el número de la foto es múltiplo de CADA_N_CUADROS (ej 3), se manda la foto a la IA.
            # Los cuadros 1 y 2 saltean esto. La aplicación "recuerda" la posición vieja y va súper rápido.
            if self.contador_cuadros % CADA_N_CUADROS == 0:
                # Envía la matriz de imagen al cerebro IA y guarda lista con nombres y posiciones
                self.ultimos = self.reconocedor.procesar(cuadro)
                # Verifica los nombres devueltos y decide si los registra o no
                self.gestionar_reconocimientos(self.ultimos)

            # Envía la foto + los nombres/posiciones a la función "componer" que las dibuja juntas
            # El resultado de ese dibujo se envía a "mostrar" que lo pega en el programa
            self.mostrar(self.componer(cuadro, self.ultimos))
        else: # Si se desconectó la cámara o tiró error el cable
            self.estado("SIN SEÑAL", "La cámara no está enviando imagen", ROJO)

        # MAGIA DE TKINTER: Obliga a esta ventana a ejecutar `self.bucle` dentro de 10 milisegundos.
        # Al llamarse a sí misma tan seguido, crea la ilusión óptica de video.
        self.after(10, self.bucle)

    def gestionar_reconocimientos(self, resultados):
        # Creamos un conjunto { } 'vistos' que guardará los nombres de esta foto específica
        # Filtramos 'None' para guardar solo los nombres que se reconocieron
        vistos = {nombre for _, nombre, _ in resultados if nombre}

        # list() crea una copia del diccionario para que podamos eliminar ítems en vivo sin que de error de loop
        for nombre in list(self.confirmaciones):
            # Si alguien estaba siendo seguido (estaba en el diccionario) y de repente sale de plano (no está en vistos)
            if nombre not in vistos:
                # Lo elimina del conteo histórico para que la próxima vez arranque de cero y no hayan falsos positivos
                del self.confirmaciones[nombre]

        # Si en la foto devuelta no hay nadie detectado
        if not resultados:
            self.estado("ESPERANDO", "Acercate a la cámara para registrar tu ingreso", AZUL, BORDE)
            return # Y rompe la ejecución de validaciones

        # any() verifica si al menos 1 resultado tuvo 'None' en el nombre
        if any(nombre is None for _, nombre, _ in resultados):
            self.estado("NO AUTORIZADO", "Persona no registrada en el taller", ROJO)

        # sorted(vistos) los ordena alfabéticamente si hay más de 1 mecánico en cámara
        for nombre in sorted(vistos):
            # .get saca el número de su contador o devuelve 0 si recién apareció. Y a eso le suma + 1 vez
            self.confirmaciones[nombre] = self.confirmaciones.get(nombre, 0) + 1

            # Si ya vino a trabajar y el diccionario 'registrados_hoy' lo tiene guardado
            if nombre in self.registrados_hoy:
                # Pone el cartel Verde gigante y le avisa a qué hora ya fichó antes
                self.estado("YA REGISTRADO",
                            f"{nombre} ingresó hoy a las {self.registrados_hoy[nombre]}", VERDE)
                            
            # Si ya se lo vio 'X' cantidad de veces SEGUIDAS (ej 3 veces)
            elif self.confirmaciones[nombre] >= CONFIRMACIONES:
                registrar_ingreso(nombre) # Función externa: abre el CSV, le anota la hora y lo guarda
                self.registrados_hoy = leer_registrados_hoy() # Refresca el diccionario interno para que aparezca ya mismo
                self.actualizar_tabla()   # Dibuja la fila en la tabla para que se actualice la pantalla
                
                # Rescata a qué hora entró para el mensaje
                hora = self.registrados_hoy.get(nombre, "")
                # Avisa con bombos y platillos el éxito en verde
                self.estado("INGRESO REGISTRADO", f"{nombre}  ·  {hora}", VERDE)
                self.sonido() # Toca el timbre (Windows)
                
            else: # Si se lo vio pero el contador está en 1 o 2 (aun está verificando)
                self.estado("RECONOCIENDO…", nombre, NARANJA)

    # ---- Dibujo sobre el video ------------------------------------
    
    def componer(self, cuadro, resultados):
        """Recibe una imagen de video de OpenCV y los resultados, los pinta encima y devuelve el PNG final"""
        # cvtColor cambia canales BGR a RGB. fromarray lo convierte en objeto Pillow, .convert('RGBA') le permite aceptar transparencias.
        base = Image.fromarray(cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB)).convert("RGBA")
        
        # Crea una foto idéntica pero invisible (el canal A de rgba = 0 es transparente)
        capa = Image.new("RGBA", base.size, (0, 0, 0, 0))
        # Seleccionamos esa capa invisible para dibujar en ella (así no tocamos la foto de los mecánicos)
        d = ImageDraw.Draw(capa)
        
        ancho, alto = base.size # Obtiene ancho y alto del video
        f_nombre, f_chica = cargar_fuente(15), cargar_fuente(13, False) # Levanta fuentes configuradas antes

        # Recorre todos los resultados devolviendo: (Y,X,Y,X) donde está la cara, el nombre detectado, y la distancia IA (se ignora _)
        for (y1, x2, y2, x1), nombre, _ in resultados:
            if nombre:
                color = VERDE
                # Si el mecánico ya vino hoy, le agrega la frase "· Presente"
                etiqueta = nombre + ("  ·  Presente" if nombre in self.registrados_hoy else "")
            else:
                color, etiqueta = ROJO, "No autorizado"

            # Dibuja el marco de la cara con una transparencia (color de hex + "55" para hacerlo transparente)
            d.rectangle((x1, y1, x2, y2), outline=color + "55", width=1)
            # Llama a la función extra para dibujarle los "brackets" gruesos a las esquinas
            dibujar_esquinas(d, (x1, y1, x2, y2), color)

            # d.textlength saca cuánto va a medir físicamente la palabra a dibujar en píxeles
            ancho_etq = int(d.textlength(texto_seguro(etiqueta, f_nombre), font=f_nombre)) + 24
            
            # ex: Si la palabra se va a salir del video por la derecha, la corre para adentro (max min limits)
            ex = max(0, min(x1, ancho - ancho_etq))
            # ey: Si el marco de la cara está muy abajo, el cartelito se dibuja *arriba* de la cabeza, si no, abajo.
            ey = y2 + 10 if y2 + 40 < alto else max(0, y1 - 38)
            
            # Dibuja el fondo del texto estilo placa redondeada color rojo/verde
            d.rounded_rectangle((ex, ey, ex + ancho_etq, ey + 28), radius=8, fill=color)
            # Imprime el texto de la etiqueta en color blanco adentro de la cajita anterior
            escribir(d, (ex + 12, ey + 14), etiqueta, f_nombre, "white")

        # Dibujo fijo de "EN VIVO" arriba a la izq. Primero caja translúcida negra 150 (opacidad)
        d.rounded_rectangle((14, 14, 112, 42), radius=14, fill=(0, 0, 0, 150))
        # El color del circulito alterna entre Rojo vivo y Rojo opaco dividiendo los fotogramas (efecto parpadeo)
        punto = ROJO if (self.contador_cuadros // 15) % 2 == 0 else "#7a2222"
        d.ellipse((26, 22, 38, 34), fill=punto) # Dibuja el circulito
        escribir(d, (46, 28), "EN VIVO", f_chica, "white") # Dibuja el texto

        # Dibujo fijo de fecha y hora formato grabación 90's. Saca la fecha:
        marca = datetime.now().strftime('%d/%m/%Y  %H:%M:%S')
        # Saca cuánto va a ocupar eso físicamente
        ancho_m = int(d.textlength(marca, font=f_chica)) + 20
        # Dibuja cajita abajo (usando el 'alto' restándole medidas para que suba del borde)
        d.rounded_rectangle((14, alto - 42, 14 + ancho_m, alto - 14), radius=8, fill=(0, 0, 0, 150))
        escribir(d, (24, alto - 28), marca, f_chica, "white")

        # .alpha_composite pega la capa transparente dibujada ARRIBA de la foto del taller mecánico
        # .convert("RGB") elimina la transparencia sobrante porque Tkinter la necesita plana. Y la devuelve.
        return Image.alpha_composite(base, capa).convert("RGB")

    def mostrar(self, imagen_pil):
        # Toma la imagen que retornó componer(), y la mete en la variable ImageTk para que Tkinter la acepte
        self.imagen_tk = ImageTk.PhotoImage(imagen_pil)
        # Sustituye la etiqueta gráfica con la nueva foto armada, dando así la ilusión de movimiento
        self.lbl_video.configure(image=self.imagen_tk)

    # ---- Acciones de los botones ------------------------------------
    def agregar_mecanico(self):
        # Si la cámara está apagada (.ultimo_cuadro vacío), frena la ejecución.
        if not self.corriendo or self.ultimo_cuadro is None:
            # Muestra un popup informativo al usuario avisando del error y termina la acción
            messagebox.showinfo("Agregar mecánico",
                                "Primero iniciá la cámara y ubicá la cara del mecánico frente a ella.")
            return

        # Saca una copia de la foto guardada "limpia", antes de que le pintaran cuadros
        cuadro = self.ultimo_cuadro.copy()
        
        # Pide a OpenCV/face_recognition que busque cuantas caras hay en la foto en ese instante
        caras = fr.face_locations(cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB))
        # Si no hay caras (0) o si hay más de una (2,3,4) frena la operación (para no guardar caras erróneas)
        if len(caras) != 1:
            messagebox.showwarning("Agregar mecánico",
                                   "Tiene que verse exactamente una cara en la cámara.")
            return

        # Abre ventana tipo Prompt pidiendo el nombre de la persona a agregar
        nombre = simpledialog.askstring("Agregar mecánico", "Nombre y apellido:", parent=self)
        if not nombre: # Si apretó Cancelar o 'X'
            return
            
        # Filtra letras raras que el sistema operativo prohíbe tener en un archivo y limpia espacios vacíos
        nombre = ''.join(c for c in nombre if c not in '\\/:*?"<>|').strip()
        if not nombre: # Si el nombre quedó vacío después de limpiar
            return

        # Une la ruta base de 'Mecanicos/' con el nombre que escribiste seguido de '.jpg'
        ruta = os.path.join(RUTA_MECANICOS, f"{nombre}.jpg")
        
        # Verifica si ya existe en la PC alguien con ese nombre. 
        # Si sí existe, abre ventana de "Sí/No", y si dice "No", corta la ejecución.
        if os.path.exists(ruta) and not messagebox.askyesno(
                "Agregar mecánico", f"Ya existe «{nombre}». ¿Reemplazar su foto?"):
            return

        # Imencode convierte la matriz matemática en un JPG virtual y .tofile la escribe al disco. 
        # Esto soluciona bugs de lectura y tildes del comando clásico cv2.imwrite
        cv2.imencode('.jpg', cuadro)[1].tofile(ruta)
        
        # Le dice a la IA "volvé a leer los archivos de la carpeta porque acabo de meter uno nuevo"
        self.reconocedor.recargar()
        self.actualizar_tabla() # Dibuja por las dudas
        
        # Fuerza un cambio de estado para mostrar cartelote verde de éxito
        self._estado_actual = None
        self.estado("MECÁNICO AGREGADO", nombre, VERDE)

    def abrir_registro(self):
        # Si no hay gente fichada, todavía no se generó el CSV (evita tirar error del sistema por querer abrir nada)
        if not os.path.isfile(ARCHIVO_REGISTRO):
            messagebox.showinfo("Registro", "Todavía no hay ingresos registrados.")
            return
            
        # sys.platform.startswith('win'): Comprueba si el código está corriendo en una PC Windows
        if sys.platform.startswith('win'):
            # Ejecuta la función de Windows que abre el archivo con la app nativa (como doble clic de ratón)
            os.startfile(ARCHIVO_REGISTRO)
        elif sys.platform == 'darwin': # Si está en Mac
            # Ejecuta comando de consola de Mac 'open archivo.csv'
            subprocess.call(['open', ARCHIVO_REGISTRO])
        else: # Si está en Linux (Ubuntu, Mint, etc.)
            # Ejecuta comando de Linux 'xdg-open archivo.csv'
            subprocess.call(['xdg-open', ARCHIVO_REGISTRO])

    def cerrar(self):
        # Apaga la cámara antes de cerrar el programa, liberando la memoria y la luz de webcam
        self.detener()
        self.destroy() # Destruye el hilo gráfico (mata a Tkinter) cerrando la app


# Este if indica que todo lo de abajo corre SOLO si abres ESTE script directamente, y no como import
if __name__ == '__main__':
    # Establece como directorio actual la carpeta de tu computadora en donde se encuentre guardado este archivo 'interfaz_taller.py'
    # Así no tirará error de que "No encuentra Mecanicos/ " 
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Instancia e inicia la ventana principal creando el ciclo de ejecución infinito (.mainloop())
    App().mainloop()