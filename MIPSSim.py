# Hansika Weerasena
# Command to run on terminal: python3 MIPSsim.py inputfilename.txt

import sys

STARTING_MEMORY_ADDRESS = 260
disassembled_memory = []
registerFile = [0] * 32
data_memory_pointer = sys.maxsize
# program_counter = 0
break_flag = False


class DataDependencyError:
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
        for key, value in self.future_memory:
            self.current_memory[key] = value
        self.future_memory = {}


class RegisterFile:
    def __init__(self):
        self.current_registers = [0] * [32]
        self.future_registers = {}

    def change(self, index, value):
        self.future_registers[index] = value

    def get(self, index):
        return self.current_registers[index]

    def propagate_values(self):
        for key, value in self.future_registers:
            self.current_registers[key] = value
        self.future_registers = {}


class Buffer:
    def __init__(self, size):
        self.size = size
        self.current_queue = []
        self.future_queue = []

    def append(self, content):
        self.future_queue.append(content)

    def pop(self, buf_id=0):
        self.future_queue.pop(buf_id)
        return self.current_queue.pop(buf_id)

    def is_full(self):
        return len(self.current_queue) >= self.size

    def get_no_empty_slots(self):
        return self.size -len(self.current_queue)

    def propagate_values(self):
        for key, value in self.future_queue:
            self.current_queue[key] = value
        self.future_queue = {}


class FetchDecodeUnit:
    def __init__(self, buf1, memory, register_file, program_counter, scoreboard):
        self.is_stalled = False
        self.buf1 = buf1
        self.memory = memory
        self.program_counter = program_counter
        self.register_file = register_file
        self.branch_inst = []
        self.program_counter = program_counter
        self.scoreboard = scoreboard
        self.inst_id = -1

    def fetch(self):
        global break_flag
        if not self.is_stalled:
            self.branch_inst = []
        if not self.is_stalled and not self.buf1.is_full():
            for i in range(max(self.buf1.getget_no_empty_slots(), 4)):
                instruction = memory[self.program_counter]
                self.program_counter += 1
                self.inst_id += 1
                if instruction[0] == 'BREAK':
                    break_flag = True
                    break
                if instruction[0] in ['J', 'BEQ', 'BNE', 'BGTZ']:
                    self.is_stalled = True
                    self.branch_inst = instruction
                    self.handle_branch_instruction(instruction)
                    break
                else:
                    self.scoreboard.add_data_delay_dependency(instruction, self.inst_id)
                    self.buf1.append([self.inst_id, instruction])
        elif self.is_stalled:
            self.handle_branch_instruction(self.branch_inst)

    def handle_branch_instruction(self, instruction):
        try:
            if instruction[0] == 'J':
                target = (int(instruction[1][1:]) - STARTING_MEMORY_ADDRESS) // 4
                self.program_counter = target
            elif instruction[0] == 'BEQ':
                rs = self.scoreboard.get_reg_value_for_branch(int(instruction[1][1:]))
                rt = self.scoreboard.get_reg_value_for_branch(int(instruction[2][1:]))
                offset = int(instruction[3][1:])
                if rt == rs:
                    self.program_counter = program_counter + offset // 4
            elif instruction[0] == 'BNE':
                rs = self.scoreboard.get_reg_value_for_branch(int(instruction[1][1:]))
                rt = self.scoreboard.get_reg_value_for_branch(int(instruction[2][1:]))
                offset = int(instruction[3][1:])
                if rt != rs:
                    self.program_counter = program_counter + offset // 4
            elif instruction[0] == 'BGTZ':
                rs = self.scoreboard.get_reg_value_for_branch(int(instruction[1][1:]))
                offset = int(instruction[2][1:])
                if rs > 0:
                    self.program_counter = program_counter + offset // 4
            self.is_stalled = False
        except DataDependencyError:
            pass


class ScoreBoard:
    def __init__(self, register_file):
        self.data_dependencies_for_branch = {}
        self.data_dependencies_for_issue = {}
        self.register_file = register_file
        self.reorder_buffer = []

    def add_entry_for_reorder_buffer(self, instruction):
        self.reorder_buffer.append(instruction)

    def add_data_issue_dependency(self, ins, ins_id):
        record_data_dependencies(ins, ins_id, self.data_dependencies_for_issue)

    def add_data_branch_dependency(self, ins, ins_id):
        record_data_dependencies(ins, ins_id, self.data_dependencies_for_branch)

    def remove_data_issue_dependency(self, ins_id):
        for key, value in self.data_dependencies_for_issue:
            if value == ins_id:
                self.data_dependencies_for_issue.pop(key)

    def remove_data_branch_dependency(self, ins_id):
        for key, value in self.data_dependencies_for_branch:
            if value == ins_id:
                self.data_dependencies_for_branch.pop(key)

    def check_reg_for_data_dependency_branch(self, reg_id):
        if reg_id in self.data_dependencies_for_branch:
            raise DataDependencyError

    def check_reg_for_data_dependency_issue(self, reg_id):
        if reg_id in self.data_dependencies_for_issue:
            raise DataDependencyError

    def get_reg_value_for_branch(self, reg_id):
        self.check_reg_for_data_dependency_branch(reg_id)
        return self.register_file[reg_id]

    def get_reg_value_for_issue(self, reg_id):
        self.check_reg_for_data_dependency_issue(reg_id)
        return self.register_file[reg_id]


class IssueUnit:
    def __init__(self):
        self.is_stalled


def record_data_dependencies(ins, ins_id, dependency_map):
    if ins[0] == 1:
        record_data_dependencies_cat_1_i(ins[1:], ins_id, dependency_map)
    elif ins[0] == 2:
        record_data_dependencies_cat_2_i(ins[1:], ins_id, dependency_map)
    else:
        record_data_dependencies_cat_3_i(ins[1:], ins_id, dependency_map)


def record_data_dependencies_cat_1_i(instruction, ins_id, dependency_map):
    if instruction[0] in ['SW', 'LW']:
        dependency_map[int(instruction[1][1:])] = ins_id
        temp = instruction[2].split('(')
        dependency_map[int(temp[1].replace(")", "")[1:])] = ins_id


def record_data_dependencies_cat_2_i(instruction, ins_id, dependency_map):
    dependency_map[int(instruction[1][1:])] = ins_id
    dependency_map[int(instruction[2][1:])] = ins_id
    if instruction[0] in ['ADD', 'SUB', 'AND', 'OR', 'MUL']:
        dependency_map[int(instruction[3][1:])] = ins_id


def record_data_dependencies_cat_3_i(instruction, ins_id, dependency_map):
    dependency_map[int(instruction[1][1:])] = ins_id
    dependency_map[int(instruction[2][1:])] = ins_id


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
    instruction_str = instruction[1]
    for component in instruction[2:-1]:
        instruction_str += " " + component + ","
    if len(instruction) > 2:
        instruction_str += " " + instruction[-1]
    return instruction_str


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
    file.write("Cycle " + str(cycle) + ":\t" + get_instruction_address(instruction_pointer) + "\t")
    file.write(get_instruction_str(disassembled_memory[instruction_pointer]))
    file.write("\n\n")
    file.write("Registers\n")
    index_r = 0
    for index, register in enumerate(registerFile):
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
    if not break_flag:
        file.write("\n")


def run_cat_1_i(instruction):
    global program_counter, instruction_pointer, break_flag
    if instruction[0] == 'J':
        target = (int(instruction[1][1:]) - STARTING_MEMORY_ADDRESS) // 4
        program_counter = target
    elif instruction[0] == 'BEQ':
        rs = registerFile[int(instruction[1][1:])]
        rt = registerFile[int(instruction[2][1:])]
        offset = int(instruction[3][1:])
        if rt == rs:
            program_counter = program_counter + offset // 4
    elif instruction[0] == 'BNE':
        rs = registerFile[int(instruction[1][1:])]
        rt = registerFile[int(instruction[2][1:])]
        offset = int(instruction[3][1:])
        if rt != rs:
            program_counter = program_counter + offset // 4
    elif instruction[0] == 'BGTZ':
        rs = registerFile[int(instruction[1][1:])]
        offset = int(instruction[2][1:])
        if rs > 0:
            program_counter = program_counter + offset // 4
    elif instruction[0] == 'SW':
        rt = registerFile[int(instruction[1][1:])]
        temp = instruction[2].split('(')
        offset = int(temp[0])
        base = registerFile[int(temp[1].replace(")", "")[1:])]
        disassembled_memory[(base + offset - STARTING_MEMORY_ADDRESS) // 4] = rt
    elif instruction[0] == 'LW':
        rt = int(instruction[1][1:])
        temp = instruction[2].split('(')
        offset = int(temp[0])
        base = registerFile[int(temp[1].replace(")", "")[1:])]
        registerFile[rt] = int(disassembled_memory[(base + offset - STARTING_MEMORY_ADDRESS) // 4])
    elif instruction[0] == 'BREAK':
        break_flag = True
    else:
        raise ValueError("Invalid Operation for Category 1")


def run_cat_2_i(instruction):
    global program_counter, instruction_pointer, break_flag
    rd = int(instruction[1][1:])
    rs = registerFile[int(instruction[2][1:])]
    rt = registerFile[int(instruction[3][1:])]
    if instruction[0] == 'ADD':
        registerFile[rd] = rs + rt
    elif instruction[0] == 'SUB':
        registerFile[rd] = rs - rt
    elif instruction[0] == 'AND':
        temp = twos_complement_to_regular(rs) & twos_complement_to_regular(rt)
        registerFile[rd] = check_to_overflow_and_correct(temp)
    elif instruction[0] == 'OR':
        temp = twos_complement_to_regular(rs) | twos_complement_to_regular(rt)
        registerFile[rd] = check_to_overflow_and_correct(temp)
    elif instruction[0] == 'SRL':
        sa = int(instruction[3][1:])
        rt = rs
        registerFile[rd] = rt >> sa
    elif instruction[0] == 'SRA':
        sa = int(instruction[3][1:])
        rt = rs
        registerFile[rd] = rt >> sa
    elif instruction[0] == 'MUL':
        registerFile[rd] = rs * rt
    else:
        raise ValueError("Invalid Operation for Category 2")


def run_cat_3_i(instruction):
    global program_counter, instruction_pointer, break_flag
    rt = int(instruction[1][1:])
    rs = registerFile[int(instruction[2][1:])]
    immediate = int(instruction[3][1:])
    if instruction[0] == 'ADDI':
        registerFile[rt] = rs + immediate
    elif instruction[0] == 'ANDI':
        temp = twos_complement_to_regular(rs) & immediate
        registerFile[rt] = check_to_overflow_and_correct(temp)
    elif instruction[0] == 'ORI':
        temp = twos_complement_to_regular(rs) | immediate
        registerFile[rt] = check_to_overflow_and_correct(temp)
    else:
        raise ValueError("Invalid Operation for Category 3")


def simulate_instruction():
    global program_counter, instruction_pointer
    ins = disassembled_memory[instruction_pointer]
    program_counter = instruction_pointer + 1
    if ins[0] == 1:
        run_cat_1_i(ins[1:])
    elif ins[0] == 2:
        run_cat_2_i(ins[1:])
    else:
        run_cat_3_i(ins[1:])


if len(sys.argv) > 1:
    file_name = sys.argv[1]
else:
    file_name = "sample.txt"

memory = read_file_line_by_line(file_name)
disassemble_memory(memory, disassembled_memory)
write_disassembled_code_to_file(memory, disassembled_memory)

filez = open("simulation.txt", 'w')

cycle = 0
while not break_flag:
    if cycle % 2 == 0:
        instruction_pointer = program_counter
        simulate_instruction()
    else:
        #complete_write_to_reg()
        write_status_to_file(filez, cycle)
    cycle += 1
filez.close()
