# Platform: MIPS32 Assembly
# Author:   Ahmad Aldasouqi
# Program:  2

	.text
	.globl main

main:	
	# Load immediate values into registers
	li $t1, 146
	li $t2, -82

	# Add values of registers and store in $t0
	add $10, $t1, $t2
	
	# Exit syscall
	li $v0, 10
	syscall
