clang++-14 -std=c++17 \
  -I/usr/lib/llvm-14/include/c++/v1 \
  -I/usr/lib/llvm-14/include \
  $(llvm-config-14 --cxxflags --ldflags --system-libs --libs core) \
  llvm_parser.cpp -o llvm_parser