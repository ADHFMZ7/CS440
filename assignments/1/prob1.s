# Platform: MIPS32 Assembly
# Author: Ahmad Aldasouqi

	.text
	.globl main

main:	
	# Load immediate values into registers
	li $t1, 3
	li $t2, 2

	# Add values of registers and store in $t0
	add $t0, $t1, $t2
	
	# Exit syscall
	li $v0, 10
	syscall
