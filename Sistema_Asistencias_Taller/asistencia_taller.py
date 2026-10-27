"""
TALLER MECANICO - Control de asistencia por reconocimiento facial (Script 2)

Toma una imagen desde la camara web, la compara con la base de datos de
mecanicos (carpeta 'Mecanicos') y, si hay coincidencia, registra el nombre
y la hora de ingreso en un archivo CSV.

Uso:
    python asistencia_taller.py                  -> usa la camara web
    python asistencia_taller.py --imagen foto.jpg -> usa una foto (para pruebas)
"""
# Importación de librerías necesarias
import csv                                # Para leer y escribir el archivo de registros
import os                                 # Para interactuar con las rutas y archivos del sistema operativo
import sys                                # Para detectar el sistema operativo (Windows/Linux) y leer parámetros de consola
from datetime import datetime             # Para obtener la fecha y hora actual del sistema

import cv2                                # OpenCV: Librería para procesamiento de imágenes y manejo de la cámara
import face_recognition as fr             # Librería de IA que detecta y compara rostros
import numpy                              # Librería matemática para manejar matrices y vectores numéricos

# --- Configuracion -----------------------------------------------------------

RUTA_MECANICOS = 'Mecanicos'              # Carpeta donde deben estar las fotos de los empleados (.jpg)
ARCHIVO_REGISTRO = 'registro_asistencias.csv' # Nombre del archivo Excel/CSV donde se guardan los horarios
TOLERANCIA = 0.6                          # Límite de distancia matemática para considerar que dos caras son la misma (menor = más estricto)
EXTENSIONES = ('.jpg', '.jpeg', '.png')   # Formatos de imagen permitidos para leer
VERDE = (0, 200, 0)                       # Color BGR (Azul, Verde, Rojo) para caras conocidas
ROJO = (0, 0, 255)                        # Color BGR para caras desconocidas
BLANCO = (255, 255, 255)                  # Color BGR para el texto


# --- Base de datos de mecanicos ----------------------------------------------

def cargar_mecanicos(ruta):
    """Lee las fotos de la carpeta y extrae el nombre desde el nombre del archivo."""
    imagenes = []
    nombres = []

    # Verifica si la carpeta existe, si no, detiene el programa
    if not os.path.isdir(ruta):
        print(f"No existe la carpeta '{ruta}'")
        sys.exit(1)

    # Recorre todos los archivos dentro de la carpeta alfabéticamente
    for archivo in sorted(os.listdir(ruta)):
        # Si el archivo no es una imagen (.jpg, .png), lo salta
        if not archivo.lower().endswith(EXTENSIONES):
            continue
        
        # Lee el archivo a nivel binario. Esto evita bugs de OpenCV en Windows cuando el nombre tiene tildes o eñes
        datos = numpy.fromfile(os.path.join(ruta, archivo), dtype=numpy.uint8)
        imagen = cv2.imdecode(datos, cv2.IMREAD_COLOR) # Convierte los datos binarios a imagen
        
        # Si la imagen está corrupta, avisa y la salta
        if imagen is None:
            print(f"No se pudo leer {archivo}, se omite")
            continue
            
        imagenes.append(imagen) # Guarda la matriz de la imagen
        nombres.append(os.path.splitext(archivo)[0]) # Guarda solo el nombre sin el '.jpg'

    return imagenes, nombres


def codificar(imagenes, nombres):
    """Codifica las caras de todas las fotos. Omite las que no tienen cara."""
    lista_codificada = []
    nombres_validos = []

    # 'zip' permite recorrer las dos listas (imagenes y nombres) al mismo tiempo
    for imagen, nombre in zip(imagenes, nombres):
        # OpenCV usa colores BGR, pero la librería face_recognition requiere RGB. Se hace la conversión.
        imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
        # Extrae los vectores matemáticos de las caras encontradas en la foto
        codificaciones = fr.face_encodings(imagen_rgb)

        # Si la foto no contiene ninguna cara visible, avisa y la salta
        if not codificaciones:
            print(f"No se encontro una cara en la foto de {nombre}, se omite")
            continue

        # Guarda la primera cara encontrada en la foto (índice 0)
        lista_codificada.append(codificaciones[0])
        nombres_validos.append(nombre)

    return lista_codificada, nombres_validos


# --- Registro de asistencia --------------------------------------------------

def registrar_ingreso(persona):
    """
    Guarda nombre, fecha y hora de ingreso en el CSV.
    Devuelve True si se registro, False si ya habia ingresado hoy.
    """
    ahora = datetime.now() # Captura el instante actual
    fecha = ahora.strftime('%d/%m/%Y') # Formatea a Día/Mes/Año
    hora = ahora.strftime('%H:%M:%S')  # Formatea a Hora:Minuto:Segundo

    existe = os.path.isfile(ARCHIVO_REGISTRO) # Chequea si el archivo CSV ya fue creado antes

    if existe:
        # Abre el archivo en modo lectura para buscar si la persona ya está
        with open(ARCHIVO_REGISTRO, newline='', encoding='utf-8') as f:
            for fila in csv.DictReader(f):
                # Si el nombre y la fecha de hoy ya están en el archivo, aborta y devuelve False
                if fila['nombre'] == persona and fila['fecha'] == fecha:
                    return False

    # Abre el archivo en modo 'a' (append/añadir al final) sin borrar lo anterior
    with open(ARCHIVO_REGISTRO, 'a', newline='', encoding='utf-8') as f:
        escritor = csv.writer(f)
        # Si el archivo es nuevo, le escribe los títulos de las columnas arriba del todo
        if not existe:
            escritor.writerow(['nombre', 'fecha', 'hora_ingreso'])
        # Escribe la fila con los datos de la persona reconocida
        escritor.writerow([persona, fecha, hora])
        
    return True # Devuelve True indicando éxito en el registro


# --- Captura de imagen -------------------------------------------------------

def capturar_camara():
    """Toma una imagen de la camara web."""
    # En Windows, CAP_DSHOW acelera el tiempo de encendido de la cámara web
    if sys.platform.startswith('win'):
        captura = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        captura = cv2.VideoCapture(0) # Para Linux o Mac

    # Bucle rápido que lee y descarta 10 fotos para que la cámara tenga tiempo de ajustar su luz y autoenfoque
    for _ in range(10):
        exito, imagen = captura.read()
        
    captura.release() # Apaga la cámara para liberar el puerto USB

    # Retorna la última foto si tuvo éxito, si no, retorna Nada (None)
    return imagen if exito else None


def dibujar_resultado(imagen, ubicacion, texto, color):
    """Dibuja el rectangulo y la etiqueta con el nombre sobre la cara."""
    y1, x2, y2, x1 = ubicacion # Desempaqueta las coordenadas (Arriba, Derecha, Abajo, Izquierda)
    
    # Dibuja el recuadro principal hueco alrededor de la cara
    cv2.rectangle(imagen, (x1, y1), (x2, y2), color, 2)
    
    # Dibuja un rectángulo relleno en la parte inferior para que sirva de fondo al texto
    cv2.rectangle(imagen, (x1, y2 - 35), (x2, y2), color, cv2.FILLED)
    
    # Escribe el nombre de la persona sobre el rectángulo relleno
    cv2.putText(imagen, texto, (x1 + 6, y2 - 6),
                cv2.FONT_HERSHEY_COMPLEX, 0.8, BLANCO, 2)


# --- Programa principal ------------------------------------------------------

def main():
    print("=== TALLER MECANICO - Control de asistencia ===")

    # 1. Preparar la memoria: lee y codifica todas las fotos de la carpeta
    mis_imagenes, nombres_mecanicos = cargar_mecanicos(RUTA_MECANICOS)
    lista_codificada, nombres_mecanicos = codificar(mis_imagenes, nombres_mecanicos)

    # Si no procesó a nadie (carpeta vacía), corta la ejecución
    if not lista_codificada:
        print("No hay mecanicos cargados en la base de datos")
        sys.exit(1)
        
    print(f"Mecanicos en la base de datos: {nombres_mecanicos}")

    # 2. Obtener imagen: Si el usuario pasó un archivo por consola, usa ese, si no, prende la webcam
    if len(sys.argv) == 3 and sys.argv[1] == '--imagen':
        imagen = cv2.imread(sys.argv[2])
    else:
        imagen = capturar_camara()

    if imagen is None:
        print("No se ha podido tomar la captura")
        sys.exit(1)

    # 3. Procesar la captura: Cambia color a RGB y busca dónde están las caras y sus fórmulas matemáticas
    imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
    caras_captura = fr.face_locations(imagen_rgb)
    caras_codificadas = fr.face_encodings(imagen_rgb, caras_captura)

    if not caras_captura:
        print("No se detecto ninguna cara en la captura")

    # 4. Comparar las caras de la foto contra las caras de la base de datos en memoria
    for cara_codif, cara_ubic in zip(caras_codificadas, caras_captura):
        # Calcula la distancia matemática entre la cara en cámara y todas las caras guardadas
        distancias = fr.face_distance(lista_codificada, cara_codif)
        # Encuentra la posición en la lista de la cara más parecida (la que tiene menor distancia)
        indice = numpy.argmin(distancias)

        # Si la distancia mínima sigue siendo mayor a la tolerancia, es un desconocido
        if distancias[indice] > TOLERANCIA:
            print("Persona no autorizada: no coincide con ningun mecanico del taller")
            dibujar_resultado(imagen, cara_ubic, "No autorizado", ROJO)
            continue # Pasa a analizar la siguiente cara en la foto

        # Si pasó la prueba de tolerancia, rescata el nombre usando el índice ganador
        nombre = nombres_mecanicos[indice]
        dibujar_resultado(imagen, cara_ubic, nombre, VERDE) # Dibuja en verde

        # 5. Intentar registrar el ingreso en el archivo CSV
        if registrar_ingreso(nombre):
            print(f"Ingreso registrado: {nombre} (distancia {distancias[indice]:.2f})")
        else:
            print(f"{nombre} ya registro su ingreso hoy")

    # 6. Muestra la imagen final con los dibujos incorporados en una ventana de Windows/Linux
    cv2.imshow("Taller Mecanico - Control de Asistencia", imagen)
    # Espera infinitamente (0) hasta que el usuario presione cualquier tecla
    cv2.waitKey(0)
    # Cierra la ventana para terminar limpiamente
    cv2.destroyAllWindows()

# Punto de entrada estándar de Python. Ejecuta 'main()' solo si se corre el archivo directamente
if __name__ == '__main__':
    main()