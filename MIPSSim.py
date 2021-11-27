# Hansika Weerasena
# Command to run on terminal: python3 MIPSsim.py inputfilename.txt
# On my honor, I have neither given nor received unauthorized aid on this assignment.

import sys

STARTING_MEMORY_ADDRESS = 260
disassembled_memory = []
data_memory_pointer = sys.maxsize
break_flag = False


class DataDependencyError(Exception):
    pass


class Memory:
    def __init__(self, memory_in):
        self.current_memory = memory_in
        self.future_memory = {}

    def change(self, index, value):
        self.future_memory[index] = value

    def get(self, index):
        return self.current_memory[index]

    def propagate_values(self):
        for key, value in self.future_memory.items():
            self.current_memory[key] = value
        self.future_memory = {}

    def print_vals(self, file):
        index_d = 0
        file.write("\nData\n")
        for index, data in enumerate(disassembled_memory[data_memory_pointer:]):
            if index % 8 == 0:
                file.write(str(STARTING_MEMORY_ADDRESS + (data_memory_pointer + index) * 4) + ":\t")
            file.write(str(data))
            if (index + 1) % 8 == 0:
                file.write("\n")
            else:
                file.write("\t")
            index_d = index
        if (index_d + 1) % 8 != 0:
            file.write("\n")


class RegisterFile:
    def __init__(self):
        self.current_registers = [0] * 32
        self.future_registers = {}

    def change(self, index, value):
        self.future_registers[index] = value

    def get(self, index):
        return self.current_registers[index]

    def propagate_values(self):
        for key, value in self.future_registers.items():
            self.current_registers[key] = value
        self.future_registers = {}

    def print_vals(self, file):
        file.write("Registers\n")
        index_r = 0
        for index, register in enumerate(self.current_registers):
            if index % 8 == 0:
                file.write("R" + "{:02d}".format(index) + ":\t")
            file.write(str(register))
            if (index + 1) % 8 == 0:
                file.write("\n")
            else:
                file.write("\t")
            index_r = index
        if (index_r + 1) % 8 != 0:
            file.write("\n")


class Buffer:
    def __init__(self, size, no):
        self.size = size
        self.current_queue = []
        self.future_queue = []
        self.no = no

    def append(self, content):
        self.future_queue.append(content)

    def pop(self, buf_id=0):
        if len(self.current_queue) == 0:
            return None
        else:
            return self.current_queue.pop(buf_id)

    def peak(self, buf_id=0):
        if len(self.current_queue) == 0:
            return None
        else:
            return self.current_queue[buf_id]

    def is_full(self):
        return len(self.current_queue) >= self.size

    def get_no_empty_slots(self):
        return self.size - len(self.current_queue)

    def is_empty(self):
        return len(self.current_queue) == 0

    def propagate_values(self):
        self.current_queue = self.current_queue + self.future_queue
        self.future_queue = []

    def print_vals(self, file):
        if self.size > 1:
            file.write("Buf" + str(self.no) + ":\n")
            for i in range(len(self.current_queue)):
                file.write("\t" + "Entry " + str(i) + ": ")
                file.write(get_instruction_str(self.current_queue[i][1]))
                file.write("\n")
            for i in range(len(self.current_queue),self.size):
                file.write("\t" + "Entry " + str(i) + ":")
                file.write("\n")
        else:
            file.write("Buf" + str(self.no) + ":")
            if len(self.current_queue) > 0:
                if self.no in [8, 6, 10]:
                    file.write(" [" + str(self.current_queue[0][1]) + ", " + str(self.current_queue[0][2]) + "]")
                else:
                    file.write(" " + get_instruction_str(self.current_queue[0][1]))
            file.write("\n")


class FetchDecodeUnit:
    def __init__(self, buf1, memory, register_file, program_counter, scoreboard):
        self.is_stalled = False
        self.buf1 = buf1
        self.memory = memory
        self.program_counter = program_counter
        self.register_file = register_file
        self.branch_inst = None
        self.scoreboard = scoreboard
        self.inst_id = -1
        self.new_ins = []
        self.local_break_flag = False

    def execute(self):

        global break_flag
        if self.local_break_flag:
            break_flag = True
        else:
            if not self.is_stalled:
                self.branch_inst = None
            if not self.is_stalled and not self.buf1.is_full():
                for i in range(min(self.buf1.get_no_empty_slots(), 4)):
                    instruction = memory.get(self.program_counter)
                    self.program_counter += 1
                    if instruction[1] == 'BREAK':
                        self.local_break_flag = True
                        break
                    if instruction[1] in ['J', 'BEQ', 'BNE', 'BGTZ']:
                        self.is_stalled = True
                        self.branch_inst = instruction
                        self.handle_branch_instruction(instruction)
                        break
                    else:
                        self.inst_id += 1
                        self.new_ins.append([self.inst_id, instruction, False])
                        self.scoreboard.add_data_branch_dependency(instruction, self.inst_id)
                        self.buf1.append([self.inst_id, instruction])
            elif self.is_stalled:
                self.handle_branch_instruction(self.branch_inst)

    def handle_branch_instruction(self, instruction):
        try:
            if instruction[1] == 'J':
                target = (int(instruction[2][1:]) - STARTING_MEMORY_ADDRESS) // 4
                self.program_counter = target
            elif instruction[1] == 'BEQ':
                rs = self.scoreboard.get_reg_value_for_branch(int(instruction[2][1:]))
                rt = self.scoreboard.get_reg_value_for_branch(int(instruction[3][1:]))
                offset = int(instruction[4][1:])
                if rt == rs:
                    self.program_counter = self.program_counter + offset // 4
            elif instruction[1] == 'BNE':
                rs = self.scoreboard.get_reg_value_for_branch(int(instruction[2][1:]))
                rt = self.scoreboard.get_reg_value_for_branch(int(instruction[3][1:]))
                offset = int(instruction[4][1:])
                if rt != rs:
                    self.program_counter = self.program_counter + offset // 4
            elif instruction[1] == 'BGTZ':
                rs = self.scoreboard.get_reg_value_for_branch(int(instruction[2][1:]))
                offset = int(instruction[2][1:])
                if rs > 0:
                    self.program_counter = self.program_counter + offset // 4
            self.is_stalled = False
        except DataDependencyError:
            pass

    def propagate_values(self):
        self.scoreboard.reorder_buffer = self.scoreboard.reorder_buffer + self.new_ins
        self.new_ins = []

    def print_vals(self, file):
        file.write("IF:\n")
        file.write("\tWaiting:")
        if self.is_stalled:
            file.write(" ")
            file.write(get_instruction_str(self.branch_inst))
        file.write("\n\tExecuted:")
        if not self.is_stalled and self.branch_inst is not None:
            file.write(" ")
            file.write(get_instruction_str(self.branch_inst))
        elif self.local_break_flag:
            file.write(" [BREAK]")
        file.write("\n")


class ScoreBoard:
    def __init__(self, register_file):
        self.data_dependencies_for_branch = {}
        self.register_file = register_file
        self.reorder_buffer = []

    def add_entry_for_reorder_buffer(self, instruction):
        self.reorder_buffer.append(instruction)

    def add_data_branch_dependency(self, ins, ins_id):
        record_data_dependencies(ins, ins_id, self.data_dependencies_for_branch)

    def remove_data_branch_dependency(self, ins_id):
        for i in list(self.data_dependencies_for_branch):
            if self.data_dependencies_for_branch[i] == ins_id:
                self.data_dependencies_for_branch.pop(i)

    def check_reg_for_data_dependency_branch(self, reg_id):
        if reg_id in self.data_dependencies_for_branch:
            raise DataDependencyError

    def get_reg_value_for_branch(self, reg_id):
        self.check_reg_for_data_dependency_branch(reg_id)
        return self.register_file.get(reg_id)

    def get_last_committed_min_id(self):
        last_committed_min_id = -1
        for idx, entry in enumerate(self.reorder_buffer):
            if not entry[2]:
                last_committed_min_id = idx - 1
                break
        return last_committed_min_id

    def have_RAW_hazard(self, indexed_ins):
        all_writing_regs = []
        for inst in self.reorder_buffer[self.get_last_committed_min_id() + 1: indexed_ins[0]]:
            if inst[0] is not indexed_ins[0]:
                all_writing_regs.append(get_writing_reg_id(inst[1]))
        for reg_id in get_reading_reg_ids(indexed_ins[1]):
            if reg_id in all_writing_regs:
                return True
        return False

    def have_WAW_hazard(self, indexed_ins):
        all_writing_regs = []
        for inst in self.reorder_buffer[self.get_last_committed_min_id() + 1: indexed_ins[0]]:
            if inst[0] is not indexed_ins[0]:
                all_writing_regs.append(get_writing_reg_id(inst[1]))
        if get_writing_reg_id(indexed_ins[1]) in all_writing_regs:
            return True
        else:
            return False

    def have_WAR_hazard(self, indexed_ins, first_in_buf):
        all_reading_regs = []
        for inst in self.reorder_buffer[first_in_buf: indexed_ins[0]]:
            all_reading_regs = all_reading_regs + get_reading_reg_ids(inst[1])
        if get_writing_reg_id(indexed_ins[1]) in all_reading_regs:
            return True
        else:
            return False


class IssueUnit:
    def __init__(self, scoreboard, register_file, buf1, buf2, buf3, buf4):
        self.register_file = register_file
        self.scoreboard = scoreboard
        self.buf1 = buf1
        self.buf2 = buf2
        self.buf3 = buf3
        self.buf4 = buf4
        self.first_in_buf = 0

    def execute(self):
        if len(self.buf1.current_queue) > 0:
            self.first_in_buf = self.buf1.peak()[0]
        current_free_buf2 = self.buf2.get_no_empty_slots()
        current_free_buf3 = self.buf3.get_no_empty_slots()
        current_free_buf4 = self.buf4.get_no_empty_slots()
        is_prev_unissued_sw = False

        idx = 0
        while idx < len(self.buf1.current_queue):
            indexed_ins = self.buf1.current_queue[idx]
            if self.instruction_eligible_to_issue(indexed_ins):
                if indexed_ins[1][1] in ['LW', 'SW']:
                    if current_free_buf2 > 0 and not is_prev_unissued_sw:
                        self.buf2.append(self.buf1.pop(idx))
                        current_free_buf2 = current_free_buf2 - 1
                        idx = idx -1
                    else:
                        is_prev_unissued_sw = True
                if indexed_ins[1][1] in ['ADD', 'SUB', 'AND', 'OR', 'SRL', 'SRA', 'ADDI', 'ANDI', 'ORI']:
                    if current_free_buf3 > 0:
                        self.buf3.append(self.buf1.pop(idx))
                        current_free_buf3 = current_free_buf3 - 1
                        idx = idx - 1
                if indexed_ins[1][1] == 'MUL':
                    if current_free_buf4 > 0:
                        self.buf4.append(self.buf1.pop(idx))
                        current_free_buf4 = current_free_buf4 - 1
                        idx = idx - 1
            idx = idx + 1

    def instruction_eligible_to_issue(self, indexed_ins):
        if self.have_data_hazards(indexed_ins):
            return False
        else:
            return True

    def have_data_hazards(self, indexed_ins):
        if self.scoreboard.have_RAW_hazard(indexed_ins):
            return True
        if self.scoreboard.have_WAW_hazard(indexed_ins):
            return True
        if self.scoreboard.have_WAR_hazard(indexed_ins, self.first_in_buf):
            return True
        return False


class ALU1:
    def __init__(self, buf2, buf5):
        self.buf2 = buf2
        self.buf5 = buf5

    def execute(self):
        indexed_instruction = self.buf2.pop()
        if indexed_instruction is not None:
            self.buf5.append(indexed_instruction)


class Mem:
    def __init__(self, buf5, buf8, memory, register_file, scoreboard):
        self.buf8 = buf8
        self.buf5 = buf5
        self.memory = memory
        self.register_file = register_file
        self.last_committed_id = None
        self.scoreboard = scoreboard

    def execute(self):
        indexed_instruction = self.buf5.pop()
        if indexed_instruction is not None:
            instruction = indexed_instruction[1]
            if instruction[1] == 'SW':
                rt = self.register_file.get(int(instruction[2][1:]))
                temp = instruction[3].split('(')
                offset = int(temp[0])
                base = self.register_file.get(int(temp[1].replace(")", "")[1:]))
                self.memory.change((base + offset - STARTING_MEMORY_ADDRESS) // 4, rt)
                self.last_committed_id = indexed_instruction[0]
            else:
                rt = int(instruction[2][1:])
                temp = instruction[3].split('(')
                offset = int(temp[0])
                base = self.register_file.get(int(temp[1].replace(")", "")[1:]))
                value = int(self.memory.get((base + offset - STARTING_MEMORY_ADDRESS) // 4))
                self.buf8.append([indexed_instruction[0], value, 'R' + str(rt)])

    def propagate_values(self):
        if self.last_committed_id is not None:
            self.scoreboard.remove_data_branch_dependency(self.last_committed_id)
            self.scoreboard.reorder_buffer[self.last_committed_id][2] = True
            self.last_committed_id = None

class ALU2:
    def __init__(self, buf3, buf6, register_file):
        self.buf6 = buf6
        self.buf3 = buf3
        self.register_file = register_file

    def execute(self):
        indexed_instruction = self.buf3.pop()
        if indexed_instruction is not None:
            instruction = indexed_instruction[1]
            ans = None
            if instruction[0] == 2:
                rd = int(instruction[2][1:])
                rs = self.register_file.get(int(instruction[3][1:]))
                rt = self.register_file.get(int(instruction[4][1:]))
                if instruction[1] == 'ADD':
                    ans = rs + rt
                elif instruction[1] == 'SUB':
                    ans = rs - rt
                elif instruction[1] == 'AND':
                    temp = twos_complement_to_regular(rs) & twos_complement_to_regular(rt)
                    ans = check_to_overflow_and_correct(temp)
                elif instruction[1] == 'OR':
                    temp = twos_complement_to_regular(rs) | twos_complement_to_regular(rt)
                    ans = check_to_overflow_and_correct(temp)
                elif instruction[1] == 'SRL':
                    sa = int(instruction[4][1:])
                    rt = rs
                    ans = rt >> sa
                elif instruction[1] == 'SRA':
                    sa = int(instruction[4][1:])
                    rt = rs
                    ans = rt >> sa
                else:
                    raise ValueError("Invalid Operation")
                self.buf6.append([indexed_instruction[0], ans, 'R' + str(rd)])
            else:
                rt = int(instruction[2][1:])
                rs = self.register_file.get(int(instruction[3][1:]))
                immediate = int(instruction[4][1:])
                if instruction[1] == 'ADDI':
                    ans = rs + immediate
                elif instruction[1] == 'ANDI':
                    temp = twos_complement_to_regular(rs) & immediate
                    ans = check_to_overflow_and_correct(temp)
                elif instruction[1] == 'ORI':
                    temp = twos_complement_to_regular(rs) | immediate
                    ans = check_to_overflow_and_correct(temp)
                else:
                    raise ValueError("Invalid Operation")
                self.buf6.append([indexed_instruction[0], ans, 'R' + str(rt)])


class Mul:
    def __init__(self, in_buf, out_buf, register_file, is_final_stage=False):
        self.in_buf = in_buf
        self.out_buf = out_buf
        self.register_file = register_file
        self.is_final_stage = is_final_stage

    def execute(self):
        indexed_instruction = self.in_buf.pop()
        if indexed_instruction is not None:
            instruction = indexed_instruction[1]
            if self.is_final_stage:
                rd = int(instruction[2][1:])
                rs = self.register_file.get(int(instruction[3][1:]))
                rt = self.register_file.get(int(instruction[4][1:]))
                ans = rs * rt
                self.out_buf.append([indexed_instruction[0], ans, 'R' + str(rd)])
            else:
                self.out_buf.append(indexed_instruction)


class WB:
    def __init__(self, in_buf1, in_buf2, in_buf3, register_file, scoreboard):
        self.in_buf1 = in_buf1
        self.in_buf2 = in_buf2
        self.in_buf3 = in_buf3
        self.register_file = register_file
        self.scoreboard = scoreboard
        self.new_committed_ids = []

    def execute(self):
        val1 = self.in_buf1.pop()
        if val1 is not None:
            self.write_back(val1)
        val2 = self.in_buf2.pop()
        if val2 is not None:
            self.write_back(val2)
        val3 = self.in_buf3.pop()
        if val3 is not None:
            self.write_back(val3)

    def write_back(self, ans):
        self.register_file.change(int(ans[2][1:]), ans[1])
        self.new_committed_ids.append(ans[0])

    def propagate_values(self):
        for ins_id in self.new_committed_ids:
            self.scoreboard.remove_data_branch_dependency(ins_id)
            self.scoreboard.reorder_buffer[ins_id][2] = True
        self.new_committed_ids = []


def record_data_dependencies(instruction, ins_id, dependency_map):
    temp = get_writing_reg_id(instruction)
    if temp is not None:
        dependency_map[temp] = ins_id


def get_writing_reg_id(instruction):
    if instruction[0] == 1:
        if instruction[1] == 'LW':
            return int(instruction[2][1:])
        else:
            return None
    else:
        return int(instruction[2][1:])


def get_reading_reg_ids(instruction):
    reading_reg_ids = []
    if instruction[1] in ['SW', 'LW']:
        temp = instruction[3].split('(')
        reading_reg_ids.append(int(temp[1].replace(")", "")[1:]))
        if instruction[1] == 'SW':
            reading_reg_ids.append(int(instruction[2][1:]))
    else:
        reading_reg_ids.append(int(instruction[3][1:]))
        if instruction[1] in ['ADD', 'SUB', 'AND', 'OR', 'MUL']:
            reading_reg_ids.append(int(instruction[4][1:]))
    return reading_reg_ids


def read_file_line_by_line(filename):
    file1 = open(filename, 'r')
    lines = file1.readlines()
    item_list = []
    for line in lines:
        item_list.append(line.strip())
    file1.close()
    return item_list


def get_instruction_address(int_pointer):
    return str(STARTING_MEMORY_ADDRESS + int_pointer * 4)


def get_instruction_str(instruction):
    instruction_str = "[" + instruction[1]
    for component in instruction[2:-1]:
        instruction_str += " " + component + ","
    if len(instruction) > 2:
        instruction_str += " " + instruction[-1]
    return instruction_str + "]"


def write_disassembled_code_to_file(memory, decoded_memory):
    open('disassembly.txt', 'w').close()
    with open('disassembly.txt', 'a') as the_file:
        for index, word in enumerate(memory):
            the_file.write(word + "\t")
            the_file.write(str(STARTING_MEMORY_ADDRESS + index * 4) + "\t")
            if index < data_memory_pointer:
                the_file.write(get_instruction_str(decoded_memory[index]))
            else:
                the_file.write(str(decoded_memory[index]))
            the_file.write("\n")


def bin_to_int(binary_str):
    return int(binary_str, 2)


def twos_complement_bin_to_int(binary_str):
    if binary_str[0] == '0':
        return bin_to_int(binary_str)
    else:
        return int(binary_str[1:], 2) - (int(binary_str[0], 2) << (len(binary_str) - 1))


def check_to_overflow_and_correct(val):
    if val >= 2147483648:
        return twos_complement_bin_to_int('{:032b}'.format(val))
    else:
        return val


def twos_complement_to_regular(val):
    if val < 0:
        return int(format((1 << 32) + val, '032b'), 2)
    else:
        return val


def disassemble_cat_one_i(word, idx):
    op_code = word[3:6]
    inst_data = word[6:]
    if op_code == '000':
        inst_index = bin_to_int("{:032b}".format((idx + 1) * 4 + STARTING_MEMORY_ADDRESS)[:4]) << 28 | bin_to_int(
            inst_data) << 2
        return [1, 'J', '#' + str(inst_index)]
    elif op_code == '001':
        offset = twos_complement_bin_to_int(inst_data[10:]) << 2
        return [1, 'BEQ', 'R' + str(bin_to_int(inst_data[:5])), 'R' + str(bin_to_int(inst_data[5:10])),
                '#' + str(offset)]
    elif op_code == '010':
        offset = twos_complement_bin_to_int(inst_data[10:]) << 2
        return [1, 'BNE', 'R' + str(bin_to_int(inst_data[:5])), 'R' + str(bin_to_int(inst_data[5:10])),
                '#' + str(offset)]
    elif op_code == '011':
        offset = twos_complement_bin_to_int(inst_data[10:]) << 2
        return [1, 'BGTZ', 'R' + str(bin_to_int(inst_data[:5])), '#' + str(offset)]
    elif op_code == '100':
        return [1, 'SW', 'R' + str(bin_to_int(inst_data[5:10])),
                str(twos_complement_bin_to_int(inst_data[10:])) + "(R" + str(bin_to_int(inst_data[:5])) + ")"]
    elif op_code == '101':
        return [1, 'LW', 'R' + str(bin_to_int(inst_data[5:10])),
                str(twos_complement_bin_to_int(inst_data[10:])) + "(R" + str(bin_to_int(inst_data[:5])) + ")"]
    elif op_code == '110':
        global data_memory_pointer
        data_memory_pointer = idx + 1
        return [1, 'BREAK']
    else:
        raise ValueError("Invalid Op Code for Category 1")


def disassemble_cat_two_i(word):
    op_code = word[3:6]
    dest = 'R' + str(bin_to_int(word[6:11]))
    src1 = 'R' + str(bin_to_int(word[11:16]))
    if op_code == '000':
        src2 = 'R' + str(bin_to_int(word[16:21]))
        return [2, "ADD", dest, src1, src2]
    elif op_code == '001':
        src2 = 'R' + str(bin_to_int(word[16:21]))
        return [2, "SUB", dest, src1, src2]
    elif op_code == '010':
        src2 = 'R' + str(bin_to_int(word[16:21]))
        return [2, "AND", dest, src1, src2]
    elif op_code == '011':
        src2 = 'R' + str(bin_to_int(word[16:21]))
        return [2, "OR", dest, src1, src2]
    elif op_code == '100':
        src2 = '#' + str(bin_to_int(word[16:21]))
        return [2, "SRL", dest, src1, src2]
    elif op_code == '101':
        src2 = '#' + str(bin_to_int(word[16:21]))
        return [2, "SRA", dest, src1, src2]
    elif op_code == '110':
        src2 = 'R' + str(bin_to_int(word[16:21]))
        return [2, "MUL", dest, src1, src2]
    else:
        raise ValueError("Invalid Op Code for Category 2")


def disassemble_cat_three_i(word):
    op_code = word[3:6]
    dest = 'R' + str(bin_to_int(word[6:11]))
    src1 = 'R' + str(bin_to_int(word[11:16]))
    if op_code == '000':
        return [3, 'ADDI', dest, src1, '#' + str(twos_complement_bin_to_int(word[16:]))]
    elif op_code == '001':
        return [3, 'ANDI', dest, src1, '#' + str(bin_to_int(word[16:]))]
    elif op_code == '010':
        return [3, 'ORI', dest, src1, '#' + str(bin_to_int(word[16:]))]
    else:
        raise ValueError("Invalid Op Code for Category 3")


def disassemble_instruction(word, idx):
    if word[0:3] == '000':
        return disassemble_cat_one_i(word, idx)
    elif word[0:3] == '001':
        return disassemble_cat_two_i(word)
    else:
        return disassemble_cat_three_i(word)


def disassemble_data(word):
    return twos_complement_bin_to_int(word)


def dissemble_word(word, idx):
    if data_memory_pointer > idx:
        return disassemble_instruction(word, idx)
    else:
        return disassemble_data(word)


def disassemble_memory(memory, dissembled_memory):
    for index, word in enumerate(memory):
        dissembled_memory.append(dissemble_word(word, index))


def write_status_to_file(file, cycle):
    file.write("--------------------" + "\n")
    file.write("Cycle " + str(cycle) + ":")
    file.write("\n\n")
    fetch_decode_unit.print_vals(file)
    buf1.print_vals(file)
    buf2.print_vals(file)
    buf3.print_vals(file)
    buf4.print_vals(file)
    buf5.print_vals(file)
    buf6.print_vals(file)
    buf7.print_vals(file)
    buf8.print_vals(file)
    buf9.print_vals(file)
    buf10.print_vals(file)
    file.write("\n")
    register_file.print_vals(file)
    memory.print_vals(file)
    if not break_flag:
        file.write("\n")


def all_buffes_not_empty(buffers):
    for buffer in buffers:
        if not buffer.is_empty():
            return True
    return False


if len(sys.argv) > 1:
    file_name = sys.argv[1]
else:
    file_name = "sample.txt"

memory_content = read_file_line_by_line(file_name)
disassemble_memory(memory_content, disassembled_memory)

memory = Memory(disassembled_memory)
register_file = RegisterFile()
buf1 = Buffer(8, 1)
buf2 = Buffer(2, 2)
buf3 = Buffer(2, 3)
buf4 = Buffer(2, 4)
buf5 = Buffer(1, 5)
buf6 = Buffer(1, 6)
buf7 = Buffer(1, 7)
buf8 = Buffer(1, 8)
buf9 = Buffer(1, 9)
buf10 = Buffer(1, 10)

buffer_list = [buf1, buf2, buf3, buf4, buf5, buf6, buf7, buf8, buf9, buf10]

scoreboard = ScoreBoard(register_file)
fetch_decode_unit = FetchDecodeUnit(buf1, memory, register_file, 0, scoreboard)
issue_unit = IssueUnit(scoreboard, register_file, buf1, buf2, buf3, buf4)
mem = Mem(buf5, buf8, memory, register_file, scoreboard)
alu1 = ALU1(buf2, buf5)
alu2 = ALU2(buf3, buf6, register_file)
mul1 = Mul(buf4, buf7, register_file)
mul2 = Mul(buf7, buf9, register_file)
mul3 = Mul(buf9, buf10, register_file, True)
wb = WB(buf8, buf6, buf10, register_file, scoreboard)

write_disassembled_code_to_file(memory_content, disassembled_memory)

filez = open("simulation.txt", 'w')

cycle = 0
while (not break_flag) or all_buffes_not_empty(buffer_list):
    recording_cycle = cycle // 2 + 1
    if cycle % 2 == 0:
        fetch_decode_unit.execute()
        issue_unit.execute()
        mem.execute()
        alu1.execute()
        alu2.execute()
        mul1.execute()
        mul2.execute()
        mul3.execute()
        wb.execute()
    else:
        fetch_decode_unit.propagate_values()
        wb.propagate_values()
        mem.propagate_values()
        memory.propagate_values()
        buf1.propagate_values()
        buf2.propagate_values()
        buf3.propagate_values()
        buf4.propagate_values()
        buf5.propagate_values()
        buf6.propagate_values()
        buf7.propagate_values()
        buf8.propagate_values()
        buf9.propagate_values()
        buf10.propagate_values()
        register_file.propagate_values()
        write_status_to_file(filez, recording_cycle)
    cycle += 1
filez.close()
