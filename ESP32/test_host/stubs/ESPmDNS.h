#pragma once
class MDNSResponder {
 public:
  bool begin(const char*) { return true; }
  bool addService(const char*, const char*, int) { return true; }
};
extern MDNSResponder MDNS;
