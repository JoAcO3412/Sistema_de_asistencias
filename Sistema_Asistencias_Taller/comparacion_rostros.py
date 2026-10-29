"""
TALLER MECANICO - Verificacion de identidad (Script 1)

Compara dos imagenes (foto de control y foto de prueba) para determinar
si la cara pertenece a la misma persona. En el taller se usaria, por ejemplo,
para validar que quien intenta ingresar es realmente el mecanico registrado.
"""
import sys                                # Librería para interactuar con el sistema (ej: cerrar el programa si hay error)
import cv2                                # OpenCV: Librería maestra para leer, mostrar y dibujar sobre imágenes
import face_recognition as fr             # Librería de IA para detectar rostros y compararlos matemáticamente

# --- Configuracion -----------------------------------------------------------

RUTA_CONTROL = 'Fotos_Prueba/FotoA.jpg'   # Ruta en el disco duro de la foto oficial del mecánico (la que ya sabemos que es él)
RUTA_PRUEBA = 'Fotos_Prueba/FotoB.jpg'    # Ruta de la foto nueva que queremos verificar si pertenece al mecánico
TOLERANCIA = 0.6                          # Límite matemático. Si la diferencia entre caras es menor a 0.6, es la misma persona.
VERDE = (0, 200, 0)                       # Código de color BGR (Azul 0, Verde 200, Rojo 0) para aprobados
ROJO = (0, 0, 255)                        # Código de color BGR (Azul 0, Verde 0, Rojo 255) para rechazados


def cargar_imagen(ruta):
    """Carga una imagen con OpenCV (formato BGR)."""
    imagen = cv2.imread(ruta)             # Le pide a OpenCV que lea el archivo de la ruta especificada
    
    # Si la variable está vacía (None), significa que la ruta está mal o el archivo no existe
    if imagen is None:
        print(f"No se pudo abrir la imagen: {ruta}")
        sys.exit(1)                       # Aborta y cierra el programa violentamente indicando un error (1)
        
    return imagen                         # Si todo salió bien, devuelve la matriz de la imagen


def analizar_cara(imagen_bgr, nombre):
    """Devuelve (ubicacion, codificacion) de la primera cara encontrada."""
    # OpenCV por defecto lee los colores invertidos (Azul, Verde, Rojo). 
    # La IA necesita (Rojo, Verde, Azul). cvtColor hace esa conversión.
    imagen_rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)

    # La IA analiza la imagen y busca coordenadas de rostros (arriba, derecha, abajo, izquierda)
    ubicaciones = fr.face_locations(imagen_rgb)
    
    # Si la lista de ubicaciones está vacía, no hay caras humanas en la foto
    if not ubicaciones:
        print(f"No se detecto ninguna cara en la {nombre}")
        sys.exit(1)                       # Cierra el programa con error

    # Toma el rostro encontrado y lo pasa a matemáticas (128 medidas). 
    # El [0] al final significa "agarrá solo a la primera persona que veas en la foto".
    codificacion = fr.face_encodings(imagen_rgb, ubicaciones)[0]
    
    # Devuelve la caja (dónde está) y el código (quién es)
    return ubicaciones[0], codificacion


def dibujar_cara(imagen, ubicacion, color):
    """Dibuja el rectangulo alrededor de la cara detectada."""
    # Desempaqueta la tupla de ubicaciones en 4 variables separadas
    arriba, derecha, abajo, izquierda = ubicacion
    
    # Le dice a OpenCV que dibuje un rectángulo en la imagen usando esas coordenadas.
    # El '2' al final es el grosor de la línea del rectángulo.
    cv2.rectangle(imagen, (izquierda, arriba), (derecha, abajo), color, 2)


def ajustar_tamano(imagen, alto_max=700):
    """Reduce la imagen si es muy grande para que entre en la pantalla del monitor."""
    # Saca la altura original de la imagen en píxeles (shape[0] es el alto, shape[1] el ancho)
    alto = imagen.shape[0]
    
    # Si la imagen ya es más chica que 700 píxeles, la deja igual
    if alto <= alto_max:
        return imagen
        
    # Regla de 3 para sacar el porcentaje de reducción (ej: si mide 1400, escala será 0.5)
    escala = alto_max / alto
    # Achica la imagen proporcionalmente en ambos ejes (fx y fy) usando esa escala
    return cv2.resize(imagen, None, fx=escala, fy=escala)


# --- Programa principal ------------------------------------------------------

# 1. Carga las dos imágenes desde el disco duro a la memoria RAM
foto_control = cargar_imagen(RUTA_CONTROL)
foto_prueba = cargar_imagen(RUTA_PRUEBA)

# 2. Manda las imágenes a la IA para que extraiga las coordenadas y el "ADN facial" de cada una
lugar_A, cara_codificada_A = analizar_cara(foto_control, "foto de control")
lugar_B, cara_codificada_B = analizar_cara(foto_prueba, "foto de prueba")

# 3. Comparacion de rostros y distancia entre sus caracteristicas
# fr.compare_faces devuelve True (Verdadero) o False (Falso) dependiendo de si superan la TOLERANCIA
resultado = fr.compare_faces([cara_codificada_A], cara_codificada_B, TOLERANCIA)[0]
# fr.face_distance devuelve el número exacto matemático de diferencia (ej: 0.35)
distancia = fr.face_distance([cara_codificada_A], cara_codificada_B)[0]

# Si el resultado es True, asigna color VERDE. Si es False, asigna color ROJO
color = VERDE if resultado else ROJO

# Llama a la función para pintar un cuadro en la foto original (siempre verde porque es la de control)
dibujar_cara(foto_control, lugar_A, VERDE)
# Llama a la función para pintar la foto nueva (verde si pasó, rojo si falló)
dibujar_cara(foto_prueba, lugar_B, color)

# Define el texto que se mostrará dependiendo del resultado True/False
estado = "MECANICO VERIFICADO" if resultado else "PERSONA NO AUTORIZADA"

# Imprime los resultados en la consola negra de texto para los programadores
print("=== TALLER MECANICO - Verificacion de identidad ===")
print(f"Resultado: {estado}")
print(f"Coincide: {resultado} | Distancia: {distancia:.2f} (tolerancia {TOLERANCIA})")

# 4. Mostrar resultado escribiéndolo visualmente sobre la imagen de prueba
# Escribe el estado (ej: "MECANICO VERIFICADO") en las coordenadas X=30, Y=50
cv2.putText(foto_prueba, estado, (30, 50),
            cv2.FONT_HERSHEY_COMPLEX, 1, color, 2)
# Escribe el número exacto de distancia debajo del título, en las coordenadas X=30, Y=90
cv2.putText(foto_prueba, f"Distancia: {distancia:.2f}", (30, 90),
            cv2.FONT_HERSHEY_COMPLEX, 0.8, color, 2)

# 5. Despliegue visual
# Crea dos ventanas en Windows/Mac para mostrar las fotos, pasándolas primero por el achicador de tamaño
cv2.imshow('Taller Mecanico - Foto de Control', ajustar_tamano(foto_control))
cv2.imshow('Taller Mecanico - Foto de Prueba', ajustar_tamano(foto_prueba))

# waitKey(0) pausa el programa infinitamente hasta que el usuario presione cualquier tecla en el teclado
cv2.waitKey(0)
# Cierra las ventanas emergentes de las fotos y termina la ejecución
cv2.destroyAllWindows()