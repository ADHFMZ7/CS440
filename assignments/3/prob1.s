# Platform: MIPS32 Assembly
# Author:   Ahmad Aldasouqi
# Program:  3

	.text
	.globl main

main:	
	# Load immediate value into registers
	li $t1, 0x1A

	# Logical left shift of t2 by 2 positions
	sll $t0, $t1, 2		

	# Exit syscall
	li $v0, 10
	syscall
