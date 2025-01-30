#include "core.h"
#include <iostream>
#include <fstream>
#include <vector>

int main(int argc, char *argv[]) {

    Core cpu;

    if (argc != 2) {
        std::cerr << "Invalid usage: please provide binary filename" << std::endl;
        return 1;
    }

    std::string file_name(argv[1]);

    std::ifstream input(file_name);
    std::vector<byte> ops(std::istreambuf_iterator<char>(input), {});

    std::cout << "Length of file in bytes: " << ops.size() << std::endl;

    cpu.load_program(ops);

    std::cout << cpu.get_reg(0) << std::endl;

}
