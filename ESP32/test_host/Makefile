# Verificación en PC (sin hardware):
#   make            -> pruebas de la máquina de estados
#   make sintaxis   -> compila TODO el firmware contra stubs de Arduino
#                      (requiere ArduinoJson: ARDUINOJSON=/ruta/ArduinoJson/src)
CXX ?= g++
FLAGS = -std=gnu++17 -Wall -Wextra -Wno-unused-parameter
AJFLAGS = -DARDUINOJSON_ENABLE_PROGMEM=0 -DARDUINOJSON_ENABLE_ARDUINO_STREAM=0 -DARDUINOJSON_ENABLE_ARDUINO_PRINT=0
ARDUINOJSON ?= ArduinoJson/src
FW = ../Dispensador_ESP32
CAM = ../../ESP32_CAM/Camara_ESP32CAM

.PHONY: pruebas sintaxis clean
pruebas: test_controlador
	./test_controlador

test_controlador: test_controlador.cpp $(FW)/Controlador.cpp $(FW)/Controlador.h $(FW)/NivelGeometria.h
	$(CXX) $(FLAGS) -O1 -o $@ test_controlador.cpp $(FW)/Controlador.cpp

sintaxis:
	@for v in 2 3; do \
	  for f in $(FW)/Controlador.cpp $(FW)/Ultrasonico.cpp $(FW)/Energia.cpp $(FW)/Dosificador.cpp $(FW)/Red.cpp $(FW)/NivelTolva.cpp; do \
	    $(CXX) $(FLAGS) -fsyntax-only $(AJFLAGS) -DARDUINO=10819 -DESP_ARDUINO_VERSION_MAJOR=$$v -Istubs -I$(ARDUINOJSON) -I$(FW) $$f || exit 1; \
	  done; \
	  $(CXX) $(FLAGS) -fsyntax-only $(AJFLAGS) -DARDUINO=10819 -DESP_ARDUINO_VERSION_MAJOR=$$v -Istubs -I$(ARDUINOJSON) -I$(FW) -x c++ $(FW)/Dispensador_ESP32.ino || exit 1; \
	  $(CXX) $(FLAGS) -fsyntax-only $(AJFLAGS) -DARDUINO=10819 -DESP_ARDUINO_VERSION_MAJOR=$$v -Istubs -I$(CAM) -x c++ $(CAM)/Camara_ESP32CAM.ino || exit 1; \
	  echo "Nucleo Arduino-ESP32 $$v.x (API): sintaxis OK"; \
	done

clean:
	rm -f test_controlador
