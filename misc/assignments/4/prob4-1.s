# Platform: MIPS32 Assembly
# Author:   Ahmad Aldasouqi
# Program:  4

# Calculates the average of the numbers in memory
# Should be 112

# Store 5 bytes in the .data segment
	.data
b1:	.byte 12
b2:	.byte 97
b3:	.byte 133
b4:	.byte 82
b5:	.byte 236
avg:    .word 0

	.text
	.globl main

main:	

	# Accummulate values into $t0
	xor $t0, $t0, $t0	

	lb $t1, b1
	add $t0, $t0, $t1	

	lb $t1, b2
	add $t0, $t0, $t1	

	lb $t1, b3
	add $t0, $t0, $t1	

	lb $t1, b4
	add $t0, $t0, $t1	

	lb $t1, b5
	add $t0, $t0, $t1	

	# Compute integer average (sum / 5)
	li $t3, 5       
	div $t0, $t3    
	mflo $t4

	# Store the average in memory
	la $t2, avg
	sw $t4, 0($t2)

	# Exit syscall
	li $v0, 10
	syscall
