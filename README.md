# Simple MIPS Simulator 

This simulator will have a disassembler and instruction-by-instruction simulator. 

- disassembler : Take a specified MIPS text file as input and generate the assembly code equivalent to the input file.
- instruction-by-instruction simulator : Generate the instruction-by-instruction simulation of the MIPS code. Outputing the contents of registers and data memories after execution of each instruction.

sample test files can be found in the \sample directory.

- sample.txt : This is the input to your program.
- sample_disassembly.txt : This is what your program should produce as disassembled output.
- sample_simulation.txt : This is what your program should output as simulation trace.

## How to Run

```
MIPSsim inputfilename.txt
```

It will produce two output files simulation.txt and disassemble.txt.

## Instructions

The MIPS Instruction Set Architecture PDF is available at \documents directory.
This simulator support following instructions with some alteration.

Your disassembler & simulator need to support the three categories of instructions shown in Table 1.

| Category- 1                      	| Category- 2                      	| Category- 3     	|
|----------------------------------	|----------------------------------	|-----------------	|
| J, BEQ, BNE, BGTZ, SW, LW, BREAK 	| ADD, SUB, AND, OR, SRL, SRA, MUL 	| ADDI, ANDI, ORI 	|

Table: Three categories of instructions


The format of Category- 1 instructions is described in Table 2. If the instruction belongs to
Category- 1 , the first three bits (leftmost bits) are always “ 000 ” followed by 3 bits Opcode. Please note
that instead of using 6 bits opcode in MIPS, this simulator use 3 bits opcode as described in Table 3. The
remaining part of the instruction binary is exactly the same as the original MIPS instruction set for that
specific instruction.

| 000  	| Opcode (3 bits) 	| Same as MIPS instruction 	|
|------	|-----------------	|--------------------------	|

Table: Format of Instructions in Category- 1


Please pay attention to the exact description of instruction formats and its interpretation in MIPS
instruction set manual. For example, in case of J instruction, the 26 bit instruction_index is shifted left
by two bits (padded with 00 at LSB side) and then the leftmost (MSB side) four bits of the delay slot

instruction are used to form the four bits (MSB side) of the target address. Since we do not use delay
slot in this simulator, treat the address of the next instruction as the address of the delay slot instruction.
Similarly, for BEQ, BNE and BGTZ instructions, the 16 bit offset is shifted left by two bits to form 18
bit signed offset that is added with the address of the next instruction to form the target address. Please
note that we do not consider delay slot for this simulator. In other words, an instruction following the
branch instruction should be treated as a regular instruction (see sample_simulation.txt).


| Instruction 	| Opcode (3 bits) 	|
|-------------	|-----------------	|
| J           	| 000             	|
| BEQ         	| 001             	|
| BNE         	| 010             	|
| BGTZ        	| 011             	|
| SW          	| 100             	|
| LW          	| 101             	|
| BREAK       	| 110             	|

Table: Opcode for Category-1 instructions

If the instruction belongs to Category- 2 which has the form “dest ← src1 op src2”, the first three bits
(leftmost three bits) are always “ 001 ” as shown in Figure 4. Then the following 5 bits serve as dest.
The next 5 bits for src 1, followed by 5 bits for src2. The src1 is always register but src2 can be register
(ADD, SUB, AND, OR, MUL) or immediate (SRL, SRA) depending on the opcode. The remaining
bits are all 0’s. The three-bit opcodes are listed in Figure 5.

001 opcode ( 3 bits) dest (5 bits) src1 (5 bits) src2 (5 bits) 00000000000
Figure 4: Format of Category-2 instructions where both sources are registers

| Instruction 	| Opcode (3 bits) 	|
|-------------	|-----------------	|
| ADD         	| 000             	|
| SUB         	| 001             	|
| AND         	| 010             	|
| OR          	| 011             	|
| SRL         	| 100             	|
| SRA         	| 101             	|
| MUL         	| 110             	|

Table: Opcode for Category-2 instructions

If the instruction belongs to Category- 3 which has the form “dest ← src1 op immediate_value”, the
first three bits (leftmost three bits) are always “ 010 ”. Then 3 bits for opcode as indicated in Figure 6.
The subsequent 5 bits serve as dest followed by 5 bits for src1. The second source operand is
immediate 16-bit value. The instruction format is shown in Table 7.


| Instruction 	| Opcode (3 bits) 	|
|-------------	|-----------------	|
| ADDI        	| 000             	|
| ANDI        	| 001             	|
| ORI         	| 010             	|

Table: Opcode for Category-3 instructions

| 010 	| Opcode (3 bits) 	| src1 (5 bits) 	| immediate_value (16 bits) 	|
|-----	|-----------------	|---------------	|---------------------------	|

Table: Format of Category-3 instructions with source2 as immediate value

Once you look at the sample_disassembly.txt, it may be confusing for you to
see that the last 16 bits of the following binary (offset) has the value of 9 but the assembly shows it as
36. This is a convention issue with MIPS. The binary always shows the actual offset ( 9 in this case)
value. However, the assembly always shows the value shifted by 2 bits to the left (i.e., multiplied by 4).

```
0000010000100010 0000000000001001 276 BEQ R1, R2, # 36
```

Please note there are also convention related confusion for other instructions. For example, in many
binary format, the destination is the middle operand, whereas the destination always shows up as the
leftmost operand in assembly instructions <opcode, dest, src1, src2>. Moreover, assume that all
unassigned register and data memory locations are 0.

All signed numbers should be interpreted using 2’s complement arithmetic. Note that the signed
numbers can be in registers, data memories or inside an instruction (e.g., the immediate field is signed
for ADDI). Most importantly, each location (register or data memory) can be treated differently based
on the context. For example, an arithmetic instruction (e.g., ADD) will treat the content of a register as
a signed number (in 2’s complement arithmetic), whereas a logical operation (e.g., AND) will treat the
same register content as an unsigned number (sequence of bits). Please go through mips.pdf to
understand how each instruction treats its operands (signed or unsigned).


