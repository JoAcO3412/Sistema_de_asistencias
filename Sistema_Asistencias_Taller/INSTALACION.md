# Instalación (Windows / Linux / macOS)

Ejecutar en la terminal, en este orden:

```bash
pip install -r requirements.txt
pip install face_recognition --no-deps
```

`face_recognition` se instala aparte y con `--no-deps` para que pip no intente compilar `dlib` (usamos `dlib-bin`, que ya viene compilado). `setuptools<81` es necesario porque `face_recognition_models` usa `pkg_resources`.

Verificar:

```bash
python -c "import cv2, numpy, face_recognition; print('Todo OK')"
```
