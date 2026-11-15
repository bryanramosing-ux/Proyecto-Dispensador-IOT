# Verificación en PC (sin hardware):
#   make            -> pruebas de la máquina de estados
#   make sintaxis   -> compila el firmware del ESP32 contra stubs de Arduino
#                      (requiere ArduinoJson: ARDUINOJSON=/ruta/ArduinoJson/src)
# La ESP32-CAM usa el servidor HTTP de ESP-IDF (esp_http_server) y solo se verifica
# con la compilación real de Espressif (arduino-cli), no contra stubs.
CXX ?= g++
FLAGS = -std=gnu++17 -Wall -Wextra -Wno-unused-parameter
AJFLAGS = -DARDUINOJSON_ENABLE_PROGMEM=0 -DARDUINOJSON_ENABLE_ARDUINO_STREAM=0 -DARDUINOJSON_ENABLE_ARDUINO_PRINT=0
ARDUINOJSON ?= ArduinoJson/src
FW = ../Dispensador_ESP32

.PHONY: pruebas sintaxis clean
pruebas: test_controlador test_dosificador_2 test_dosificador_3 test_historial
	./test_controlador
	./test_dosificador_2
	./test_dosificador_3
	./test_historial

test_dosificador_%: test_dosificador.cpp $(FW)/Dosificador.cpp $(FW)/Dosificador.h $(FW)/config.h
	$(CXX) $(FLAGS) -O1 -DESP_ARDUINO_VERSION_MAJOR=$* -Istubs -o $@ test_dosificador.cpp $(FW)/Dosificador.cpp

test_historial: test_historial.cpp $(FW)/HistorialNVS.h stubs/Preferences.h
	$(CXX) $(FLAGS) -O1 -Istubs -o $@ test_historial.cpp

test_controlador: test_controlador.cpp $(FW)/Controlador.cpp $(FW)/Controlador.h $(FW)/NivelGeometria.h
	$(CXX) $(FLAGS) -O1 -o $@ test_controlador.cpp $(FW)/Controlador.cpp

sintaxis:
	@for v in 2 3; do \
	  for f in $(FW)/Controlador.cpp $(FW)/Ultrasonico.cpp $(FW)/Energia.cpp $(FW)/Dosificador.cpp $(FW)/Red.cpp $(FW)/NivelTolva.cpp; do \
	    $(CXX) $(FLAGS) -fsyntax-only $(AJFLAGS) -DARDUINO=10819 -DESP_ARDUINO_VERSION_MAJOR=$$v -Istubs -I$(ARDUINOJSON) -I$(FW) $$f || exit 1; \
	  done; \
	  $(CXX) $(FLAGS) -fsyntax-only $(AJFLAGS) -DARDUINO=10819 -DESP_ARDUINO_VERSION_MAJOR=$$v -Istubs -I$(ARDUINOJSON) -I$(FW) -x c++ $(FW)/Dispensador_ESP32.ino || exit 1; \
	  echo "Nucleo Arduino-ESP32 $$v.x (API): sintaxis OK"; \
	done

clean:
	rm -f test_controlador test_dosificador_2 test_dosificador_3 test_historial
