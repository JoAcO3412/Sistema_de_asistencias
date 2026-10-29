# Sistema de Asistencia para Taller Mecánico (Reconocimiento Facial)

Este proyecto es un sistema informático diseñado para registrar el ingreso y asistencia del personal de un taller mecánico de manera automática, utilizando **Inteligencia Artificial y Visión Computacional** (Reconocimiento Facial) en tiempo real. 

Cuenta con una Interfaz Gráfica de Usuario (GUI) moderna e intuitiva que permite interactuar con la cámara, añadir nuevos empleados al sistema y visualizar los registros exportados en formato CSV.

---

## Requisitos Previos

Para ejecutar este proyecto en tu computadora, necesitarás lo siguiente:

1. **Hardware**: Una cámara web (webcam) conectada y funcional.
2. **Software**: [Python 3.8 o superior](https://www.python.org/downloads/) instalado en tu sistema.
3. **Herramientas de compilación (Solo Windows)**: La librería de inteligencia artificial requiere compilar C++. Si estás en Windows, asegúrate de tener instalado *Visual Studio Build Tools* (con la carga de trabajo de desarrollo para el escritorio con C++) y *CMake*.

---

## Instalación de Dependencias

El sistema utiliza varias librerías externas que deben ser instaladas. Abre tu terminal (Símbolo del sistema, PowerShell o Bash) y ejecuta el siguiente comando:

```bash
pip install opencv-python face_recognition numpy Pillow
