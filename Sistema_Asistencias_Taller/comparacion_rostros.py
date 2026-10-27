"""
TALLER MECANICO - Verificacion de identidad (Script 1)

Compara dos imagenes (foto de control y foto de prueba) para determinar
si la cara pertenece a la misma persona. En el taller se usaria, por ejemplo,
para validar que quien intenta ingresar es realmente el mecanico registrado.
"""
import sys
import cv2
import face_recognition as fr

# --- Configuracion -----------------------------------------------------------
RUTA_CONTROL = 'Fotos_Prueba/FotoA.jpg'   # foto registrada del mecanico
RUTA_PRUEBA = 'Fotos_Prueba/FotoB.jpg'    # foto a verificar
TOLERANCIA = 0.6                          # menor valor = comparacion mas estricta
VERDE = (0, 200, 0)
ROJO = (0, 0, 255)


def cargar_imagen(ruta):
    """Carga una imagen con OpenCV (formato BGR)."""
    imagen = cv2.imread(ruta)
    if imagen is None:
        print(f"No se pudo abrir la imagen: {ruta}")
        sys.exit(1)
    return imagen


def analizar_cara(imagen_bgr, nombre):
    """Devuelve (ubicacion, codificacion) de la primera cara encontrada."""
    # OpenCV trabaja en BGR y face_recognition en RGB -> hay que convertir
    imagen_rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)

    ubicaciones = fr.face_locations(imagen_rgb)
    if not ubicaciones:
        print(f"No se detecto ninguna cara en la {nombre}")
        sys.exit(1)

    codificacion = fr.face_encodings(imagen_rgb, ubicaciones)[0]
    return ubicaciones[0], codificacion


def dibujar_cara(imagen, ubicacion, color):
    """Dibuja el rectangulo alrededor de la cara detectada."""
    arriba, derecha, abajo, izquierda = ubicacion
    cv2.rectangle(imagen, (izquierda, arriba), (derecha, abajo), color, 2)


def ajustar_tamano(imagen, alto_max=700):
    """Reduce la imagen si es muy grande para que entre en pantalla."""
    alto = imagen.shape[0]
    if alto <= alto_max:
        return imagen
    escala = alto_max / alto
    return cv2.resize(imagen, None, fx=escala, fy=escala)


# --- Programa principal ------------------------------------------------------
foto_control = cargar_imagen(RUTA_CONTROL)
foto_prueba = cargar_imagen(RUTA_PRUEBA)

lugar_A, cara_codificada_A = analizar_cara(foto_control, "foto de control")
lugar_B, cara_codificada_B = analizar_cara(foto_prueba, "foto de prueba")

# Comparacion de rostros y distancia entre sus caracteristicas
resultado = fr.compare_faces([cara_codificada_A], cara_codificada_B, TOLERANCIA)[0]
distancia = fr.face_distance([cara_codificada_A], cara_codificada_B)[0]

color = VERDE if resultado else ROJO
dibujar_cara(foto_control, lugar_A, VERDE)
dibujar_cara(foto_prueba, lugar_B, color)

estado = "MECANICO VERIFICADO" if resultado else "PERSONA NO AUTORIZADA"
print("=== TALLER MECANICO - Verificacion de identidad ===")
print(f"Resultado: {estado}")
print(f"Coincide: {resultado} | Distancia: {distancia:.2f} (tolerancia {TOLERANCIA})")

# Mostrar resultado sobre la imagen de prueba
cv2.putText(foto_prueba, estado, (30, 50),
            cv2.FONT_HERSHEY_COMPLEX, 1, color, 2)
cv2.putText(foto_prueba, f"Distancia: {distancia:.2f}", (30, 90),
            cv2.FONT_HERSHEY_COMPLEX, 0.8, color, 2)

cv2.imshow('Taller Mecanico - Foto de Control', ajustar_tamano(foto_control))
cv2.imshow('Taller Mecanico - Foto de Prueba', ajustar_tamano(foto_prueba))

# Mantener el programa abierto hasta presionar una tecla
cv2.waitKey(0)
cv2.destroyAllWindows()
