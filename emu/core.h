#ifndef CORE_H
#define CORE_H

#include <cstdlib>
#include <vector>

#define MEM_SIZE 

using word = uint32_t;
using byte = char;

#include <cstdint>
class Core {

public:

    Core() {
        gp[0] = 0;
    }



    bool load_program(std::vector<byte> program) {

        for (int ix = 0; ix < program.size(); ++ix) {
             
        }

    }


    // mmu functions 
    byte get_word(word addr) {
        // maps virtual address to physical address
        
        return 0;
    }

    void put_word (word addr, byte value) {
        
        

    }

    word get_reg(word reg_num) {

        if (reg_num < 0 || reg_num >= 32) {
            // throw exception or something?
        }

        if (reg_num == 0) {
            return (unsigned) 0;
        }
        return gp[reg_num];
    }

    void set_reg(word reg_num, byte new_val) {
        if (reg_num == 0) {
            // Not allowed, $0 is hardwired to 0
            return;
        }

        gp[reg_num] = new_val;
        return;
    }

private:

    word pc; 
    word hi; 
    word lo; 

    // General Purpose Registers
    word gp[32];
    word memory[MEM_SIZE];
};


#endif
