"""
TALLER MECANICO - Control de asistencia por reconocimiento facial (Script 2)

Toma una imagen desde la camara web, la compara con la base de datos de
mecanicos (carpeta 'Mecanicos') y, si hay coincidencia, registra el nombre
y la hora de ingreso en un archivo CSV.

Uso:
    python asistencia_taller.py                  -> usa la camara web
    python asistencia_taller.py --imagen foto.jpg -> usa una foto (para pruebas)
"""
import csv
import os
import sys
from datetime import datetime

import cv2
import face_recognition as fr
import numpy

# --- Configuracion -----------------------------------------------------------
RUTA_MECANICOS = 'Mecanicos'
ARCHIVO_REGISTRO = 'registro_asistencias.csv'
TOLERANCIA = 0.6
EXTENSIONES = ('.jpg', '.jpeg', '.png')
VERDE = (0, 200, 0)
ROJO = (0, 0, 255)
BLANCO = (255, 255, 255)


# --- Base de datos de mecanicos ----------------------------------------------
def cargar_mecanicos(ruta):
    """Lee las fotos de la carpeta y extrae el nombre desde el nombre del archivo."""
    imagenes = []
    nombres = []

    if not os.path.isdir(ruta):
        print(f"No existe la carpeta '{ruta}'")
        sys.exit(1)

    for archivo in sorted(os.listdir(ruta)):
        if not archivo.lower().endswith(EXTENSIONES):
            continue
        # imdecode + fromfile permite nombres con tildes o ñ en Windows
        datos = numpy.fromfile(os.path.join(ruta, archivo), dtype=numpy.uint8)
        imagen = cv2.imdecode(datos, cv2.IMREAD_COLOR)
        if imagen is None:
            print(f"No se pudo leer {archivo}, se omite")
            continue
        imagenes.append(imagen)
        nombres.append(os.path.splitext(archivo)[0])

    return imagenes, nombres


def codificar(imagenes, nombres):
    """Codifica las caras de todas las fotos. Omite las que no tienen cara."""
    lista_codificada = []
    nombres_validos = []

    for imagen, nombre in zip(imagenes, nombres):
        # Pasar la imagen de BGR a RGB
        imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
        codificaciones = fr.face_encodings(imagen_rgb)

        if not codificaciones:
            print(f"No se encontro una cara en la foto de {nombre}, se omite")
            continue

        lista_codificada.append(codificaciones[0])
        nombres_validos.append(nombre)

    return lista_codificada, nombres_validos


# --- Registro de asistencia --------------------------------------------------
def registrar_ingreso(persona):
    """
    Guarda nombre, fecha y hora de ingreso en el CSV.
    Devuelve True si se registro, False si ya habia ingresado hoy.
    """
    ahora = datetime.now()
    fecha = ahora.strftime('%d/%m/%Y')
    hora = ahora.strftime('%H:%M:%S')

    existe = os.path.isfile(ARCHIVO_REGISTRO)

    if existe:
        with open(ARCHIVO_REGISTRO, newline='', encoding='utf-8') as f:
            for fila in csv.DictReader(f):
                if fila['nombre'] == persona and fila['fecha'] == fecha:
                    return False

    with open(ARCHIVO_REGISTRO, 'a', newline='', encoding='utf-8') as f:
        escritor = csv.writer(f)
        if not existe:
            escritor.writerow(['nombre', 'fecha', 'hora_ingreso'])
        escritor.writerow([persona, fecha, hora])
    return True


# --- Captura de imagen -------------------------------------------------------
def capturar_camara():
    """Toma una imagen de la camara web."""
    if sys.platform.startswith('win'):
        captura = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        captura = cv2.VideoCapture(0)

    # Descartar los primeros cuadros: la camara necesita unos instantes para ajustar la luz
    for _ in range(10):
        exito, imagen = captura.read()
    captura.release()

    return imagen if exito else None


def dibujar_resultado(imagen, ubicacion, texto, color):
    """Dibuja el rectangulo y la etiqueta con el nombre sobre la cara."""
    y1, x2, y2, x1 = ubicacion
    cv2.rectangle(imagen, (x1, y1), (x2, y2), color, 2)
    cv2.rectangle(imagen, (x1, y2 - 35), (x2, y2), color, cv2.FILLED)
    cv2.putText(imagen, texto, (x1 + 6, y2 - 6),
                cv2.FONT_HERSHEY_COMPLEX, 0.8, BLANCO, 2)


# --- Programa principal ------------------------------------------------------
def main():
    print("=== TALLER MECANICO - Control de asistencia ===")

    mis_imagenes, nombres_mecanicos = cargar_mecanicos(RUTA_MECANICOS)
    lista_codificada, nombres_mecanicos = codificar(mis_imagenes, nombres_mecanicos)

    if not lista_codificada:
        print("No hay mecanicos cargados en la base de datos")
        sys.exit(1)
    print(f"Mecanicos en la base de datos: {nombres_mecanicos}")

    # Obtener imagen (camara web o archivo de prueba)
    if len(sys.argv) == 3 and sys.argv[1] == '--imagen':
        imagen = cv2.imread(sys.argv[2])
    else:
        imagen = capturar_camara()

    if imagen is None:
        print("No se ha podido tomar la captura")
        sys.exit(1)

    # Reconocer y codificar las caras de la captura
    imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
    caras_captura = fr.face_locations(imagen_rgb)
    caras_codificadas = fr.face_encodings(imagen_rgb, caras_captura)

    if not caras_captura:
        print("No se detecto ninguna cara en la captura")

    # Buscar coincidencias
    for cara_codif, cara_ubic in zip(caras_codificadas, caras_captura):
        distancias = fr.face_distance(lista_codificada, cara_codif)
        indice = numpy.argmin(distancias)

        if distancias[indice] > TOLERANCIA:
            print("Persona no autorizada: no coincide con ningun mecanico del taller")
            dibujar_resultado(imagen, cara_ubic, "No autorizado", ROJO)
            continue

        nombre = nombres_mecanicos[indice]
        dibujar_resultado(imagen, cara_ubic, nombre, VERDE)

        if registrar_ingreso(nombre):
            print(f"Ingreso registrado: {nombre} (distancia {distancias[indice]:.2f})")
        else:
            print(f"{nombre} ya registro su ingreso hoy")

    cv2.imshow("Taller Mecanico - Control de Asistencia", imagen)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
