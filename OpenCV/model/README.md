# Modelo

Esta carpeta guarda el modelo y las etiquetas. **No se suben a GitHub** (14 MB);
se descargan y verifican (SHA-256) con:

```bash
cd OpenCV
python descargar_modelo.py
```

| Archivo | Origen | Licencia |
|---|---|---|
| `mobilenetv2-12.onnx` | ONNX Model Zoo – MobileNetV2 (ImageNet-1k) | Apache-2.0 |
| `imagenet_classes.txt` | Lista de 1000 clases ImageNet (repositorio `pytorch/hub`) | BSD |
