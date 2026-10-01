// NivelGeometria.h - Conversión de ALTURA de alimento a VOLUMEN restante.
//
// La tolva es un embudo: cerca del fondo hay muy poco alimento por cada
// centímetro de altura. Con el 20 % de la altura queda solo ~5 % del volumen,
// así que las alertas se calculan sobre el VOLUMEN, no sobre la distancia.
//
// Tabla generada por Mechanical/generar_stl.py a partir del modelo 3D
// (volumen entre la boca del embudo y la línea MAX, en pasos de 10 % de altura).
// Si cambia la geometría de la tolva, el generador avisa y muestra la tabla nueva.
#pragma once

static const float TABLA_VOLUMEN_TOLVA[11] = {0.0f, 1.6f, 4.4f, 8.5f, 14.3f, 22.0f,
                                              32.0f, 44.5f, 59.8f, 78.2f, 100.0f};

// alturaPct: 0 = boca del embudo (vacía), 100 = línea MAX. Devuelve % de volumen.
inline float alturaAVolumenPct(float alturaPct) {
  if (alturaPct <= 0.0f) return 0.0f;
  if (alturaPct >= 100.0f) return 100.0f;
  int i = (int)(alturaPct / 10.0f);
  float f = (alturaPct - i * 10.0f) / 10.0f;
  return TABLA_VOLUMEN_TOLVA[i] + f * (TABLA_VOLUMEN_TOLVA[i + 1] - TABLA_VOLUMEN_TOLVA[i]);
}
