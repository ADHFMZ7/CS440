# Platform: MIPS32 Assembly
# Author: Ahmad Aldasouqi

	.text
	.globl main

main:
	# Load the value 0xF0 in the $8 register
	li  $8, 0xF0

	# OR $8 with 0x0F and store the result in $9
	ori $9, $8, 0x0F

	# Exit syscall
	li $v0, 10
	syscall
