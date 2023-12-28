from queue import Queue
import sys

class Codewriter:

    _segment_asm = {
            "local"     : "LCL",
            "argument"  : "ARG",
            "this"      : "THIS",
            "that"      : "THAT",
            "pointer"   :   3,
            "temp"      :   5
        }

    def __init__(self):
        self.code_writer_queue = Queue()
        self.index = 0
        self.return_address = 0
        
    def end_operation(self):
        self._code_vm_end()
    
 # Branching Operation

    def write_label_name(self, label_name):
        self.code_writer_queue.put("// label " + label_name)
        self.code_writer_queue.put("({0})".format(label_name))
        self.code_writer_queue.put("\n")
    
    def write_goto_label(self, label_name):
        self.code_writer_queue.put("// goto " + label_name)
        self.code_writer_queue.put("@{0}".format(label_name))
        self.code_writer_queue.put("0;JMP")
        self.code_writer_queue.put("\n")

    def write_if_goto_label(self, label_name):
        self.code_writer_queue.put("// if-goto " + label_name)
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("AM=M-1")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@{0}".format(label_name))
        self.code_writer_queue.put("D;JNE")
        self.code_writer_queue.put("\n")

    def write_call(self, function_name, n_args):
        self.code_writer_queue.put("//  call {0} {1}\n".format(function_name, n_args))

        #push returnAddress: generate a label and push it to the stack
        self.code_writer_queue.put("//  push returnAddress")
        self.code_writer_queue.put("@RA{0}".format(self.return_address))
        self.code_writer_queue.put("D=A")
        self._write_call_template()

        #push LCL: saves LCL of the caller
        self.code_writer_queue.put("//  push LCL")
        self.code_writer_queue.put("@LCL")
        self.code_writer_queue.put("D=M")
        self._write_call_template()

        #push ARG: saves ARG of the caller
        self.code_writer_queue.put("//  push ARG")
        self.code_writer_queue.put("@ARG")
        self.code_writer_queue.put("D=M")
        self._write_call_template()

        #push THIS: saves THIS of the caller
        self.code_writer_queue.put("//  push THIS")
        self.code_writer_queue.put("@THIS")
        self.code_writer_queue.put("D=M")
        self._write_call_template()       
    
        #push THAT: saves THIS of the caller
        self.code_writer_queue.put("//  push THAT")
        self.code_writer_queue.put("@THAT")
        self.code_writer_queue.put("D=M")
        self._write_call_template()  

        #repositions ARG
        self.code_writer_queue.put("//  ARG = SP-5-nArgs")
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@5")
        self.code_writer_queue.put("D=D-A")
        self.code_writer_queue.put("@{0}".format(n_args))
        self.code_writer_queue.put("D=D-A")
        self.code_writer_queue.put("@ARG")
        self.code_writer_queue.put("M=D")
        self.code_writer_queue.put("\n")

        #repositions LCL
        self.code_writer_queue.put("//  LCL=SP")
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@LCL")
        self.code_writer_queue.put("M=D")
        self.code_writer_queue.put("\n")

        #transfer control to the callee
        self.write_goto_label(function_name)

        #injects the return address label into the code
        self.write_label_name(str(self.return_address))

        self.return_address += 1
        
    def write_function(self, function_name, n_args):
        self.code_writer_queue.put("//  function {0} {1}".format(function_name, n_args))
        self.write_label_name(function_name)

        for _ in range(int(n_args)):
            self.code_writer_queue.put("@SP")
            self.code_writer_queue.put("AM=M+1")
            self.code_writer_queue.put("A=A-1")
            self.code_writer_queue.put("M=0")
        self.code_writer_queue.put("\n")

    def write_return(self):
        #frame=LCL ---- frame is a temporary variable
        self.code_writer_queue.put("// return")
        self.code_writer_queue.put("// frame=LCL\n")
        self.code_writer_queue.put("LCL")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@R13")
        self.code_writer_queue.put("M=D\n")

        #retAddr = *(frame-5)---- puts the return address in a temporary variable
        self.code_writer_queue.put("// retAddr = *(frame-5)")
        self.code_writer_queue.put("@13")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@5")
        self.code_writer_queue.put("A=D-A")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@R14")
        self.code_writer_queue.put("M=D\n")

        #*ARG=pop() ---- repositions the return value for the caller
        self.code_writer_queue.put("// *ARG=pop()")
        self.code_writer_queue.put("SP")
        self.code_writer_queue.put("AM=M-1")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@ARG")
        self.code_writer_queue.put("M=D\n")  

        #SP=ARG+1 ---- repositions SP for the caller
        self.code_writer_queue.put("// SP=ARG+1")
        self.code_writer_queue.put("@ARG")
        self.code_writer_queue.put("D=M+1")
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("M=D\n")

        #THAT=*(frame-1) ---- restores THAT for the caller
        self.code_writer_queue.put("// THAT=*(frame-1)")
        self._return_template("THAT", 1)

        #THIS=*(frame-2) ---- restores THIS for the caller
        self.code_writer_queue.put("// THIS=*(frame-2)")
        self._return_template("THIS", 2)

        #ARG=*(frame-3) ---- restores THIS for the caller
        self.code_writer_queue.put("// ARG=*(frame-3)")
        self._return_template("ARG", 3)

        #LCL=*(frame-4) ---- restores LCL for the caller
        self.code_writer_queue.put("// LCL=*(frame-4)")
        self._return_template("LCL", 4)

        #goto retAddr ---- go to the return address
        self.code_writer_queue.put("// goto retAddr")
        self.code_writer_queue.put("@R14")
        self.code_writer_queue.put("A=M")
        self.code_writer_queue.put("0;JMP\n")

#Arithmetic operation 
    
    def write_arithmetic(self, operation):
        """
        when comand type is a C_ARITHMETIC:

        """
        if operation == "add":
            self._code_vm_add()
        elif operation == "neg":
            self._code_vm_neg()
        elif operation == "sub":
            self._code_vm_sub()
        elif operation == "eq":
            self._code_vm_eq()
        elif operation == "gt":
            self._code_vm_gt()
        elif operation == "lt":
            self._code_vm_lt()
        elif operation == "and":
            self._code_vm_and()
        elif operation == "or":
            self._code_vm_or()
        elif operation == "not":
            self._code_vm_not()
        else:
            raise ValueError("Invalid arithmetic command!")

# Push and Pop Operations

    def push_operation(self, segment, offset):
        """
        Push template for constant, static, local, argument, this, that, pointer, temp

        constant: A truly a virtual segment: Access to constant i is implemented by supplying the constant i.

        static: mapped on RAM[16 ... 255]; each segment reference static i appearing in a VM file named f is compiled to the assembly language symbol f.i
                pushing a static i  is as simple as getting the value at its associated address f.i and pushing it onto the stack

        local, argument, this, that:  these method-level segments are mapped somewhere from address 2048 onward, in an area called “heap”.
                                      the base addresses of these segments are kept in RAM addresses LCL, ARG, THIS, and THAT.
                                      access to the i-th entry of any of these segments is implemented by accessing RAM[segmentBase + i]
        
        pointer, temp: these segments are each mapped directly onto a fixed area in the RAM.
                       the pointer segment is mapped on RAM locations 3-4 (also called THIS and THAT).

        Args:
            segment (string): one of static argument local this that temp pointer
            offset (int): third argument constant

        """

        if segment == "constant":
            self.code_writer_queue.put("// push " + segment + " " + str(offset))
            self.code_writer_queue.put("@" + str(offset))
            self.code_writer_queue.put("D=A")

        elif segment == "static":
            self.code_writer_queue.put("// push " + segment + " " + str(offset))
            self.code_writer_queue.put("@" + sys.argv[1].split(".")[0] + "." + str(offset))
            self.code_writer_queue.put("D=M")

        elif segment in ["local", "argument", "this", "that"]:
            self.code_writer_queue.put("// push " + segment + " " + str(offset))
            self.code_writer_queue.put("@" + self._segment_asm[segment])
            self.code_writer_queue.put("D=M")
            self.code_writer_queue.put("@" + str(offset))
            self.code_writer_queue.put("A=D+A")
            self.code_writer_queue.put("D=M")    

        elif segment in ["pointer", "temp"]:
            self.code_writer_queue.put("// push " + segment + " " + str(offset))
            self.code_writer_queue.put("@R" + str(offset + self._segment_asm[segment]))
            self.code_writer_queue.put("D=M")

        else:
            raise ValueError("Invalid Hack assembly code detected!")
        
        # Same asm code block
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("A=M")
        self.code_writer_queue.put("M=D")
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("M=M+1")
        self.code_writer_queue.put("\n") 

    def pop_operation(self, segment, offset):
        """
        Pop template for static, local, argument, this, that, pointer, temp

        static: mapped on RAM[16 ... 255]; each segment reference static i appearing in a VM file named f is compiled to the assembly language symbol f.i
                to pop static i the stack pointer SP is decremented and the value contained at the new stack location is stored in f.i

        local, argument, this, that:  these method-level segments are mapped somewhere from address 2048 onward, in an area called “heap”.
                                      the base addresses of these segments are kept in RAM addresses LCL, ARG, THIS, and THAT.
                                      access to the i-th entry of any of these segments is implemented by accessing RAM[segmentBase + i]
        
        pointer, temp: these segments are each mapped directly onto a fixed area in the RAM.
                       the pointer segment is mapped on RAM locations 3-4 (also called THIS and THAT).

        Args:
            segment (string): one of static argument local this that temp pointer
            offset (int): third argument constant

        """

        if segment == "static":
            self.code_writer_queue.put("// pop " + segment + " " + str(offset))
            self.code_writer_queue.put("@SP")
            self.code_writer_queue.put("AM=M-1")
            self.code_writer_queue.put("D=M")
            self.code_writer_queue.put("@" + sys.argv[1].split(".")[0] + "." + str(offset))
            self.code_writer_queue.put("M=D")
            
        elif segment in ["local", "argument", "this", "that"]:
            self.code_writer_queue.put("// pop " + segment + " " + str(offset))
            self.code_writer_queue.put("@" + self._segment_asm[segment])
            self.code_writer_queue.put("D=M")
            self.code_writer_queue.put("@" + str(offset))
            self.code_writer_queue.put("D=D+A")
            self.code_writer_queue.put("@R13")
            self.code_writer_queue.put("M=D")
            self.code_writer_queue.put("@SP")
            self.code_writer_queue.put("AM=M-1")
            self.code_writer_queue.put("D=M")
            self.code_writer_queue.put("@R13")
            self.code_writer_queue.put("A=M")
            self.code_writer_queue.put("M=D")

        elif segment in ["pointer", "temp"]:
            self.code_writer_queue.put("// pop " + segment + " " + str(offset))
            self.code_writer_queue.put("@SP")
            self.code_writer_queue.put("AM=M-1")
            self.code_writer_queue.put("D=M")
            self.code_writer_queue.put("@R" + str(offset + self._segment_asm[segment]))
            self.code_writer_queue.put("M=D")
        else:
            raise ValueError("Invalid Hack assembly code detected!")
        
# Arithmetic Operations
        
    def _code_vm_add(self):
        self._add_sub_template("add", "D+M")
    
    def _code_vm_sub(self):
        self._add_sub_template("sub", "M-D")

    def _code_vm_neg(self):
        self._neg_not_template("neg", "-M")
    
    def _code_vm_eq(self):
        self._eq_gt_lt_template("eq", "JEQ")

    def _code_vm_gt(self):
        self._eq_gt_lt_template("gt", "JGT")

    def _code_vm_lt(self):
        self._eq_gt_lt_template("lt", "JLT")

    def _code_vm_and(self):
        self._and_or_template("and", "D&M")

    def _code_vm_or(self):
        self._and_or_template("or", "D|M")
    
    def _code_vm_not(self):
        self._neg_not_template("not", "!M")

    def _code_vm_end(self):
        self._end_template()


#templates
    
    def _return_template(self, segment, index):
        self.code_writer_queue.put("@13")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@{0}".format(index))
        self.code_writer_queue.put("A=D-A")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@{0}".format(segment))
        self.code_writer_queue.put("M=D\n")

    def _write_call_template(self):
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("AM=M+1")
        self.code_writer_queue.put("@A=A-1")
        self.code_writer_queue.put("M=D")
        self.code_writer_queue.put("\n")

    def _eq_gt_lt_template(self, cmd, jmp):
        """
        Template that works for eq, gt and lt

        Args:
            cmd (string): for comment, to indicate the operation of hack assembly language produced
            jmp (string): the jump variable corresponds to the specific operation. eq : JEQ, gt : JGT, lt : JLT

        """
        self.code_writer_queue.put("//" + cmd)
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("AM=M-1")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("AM=M-1")
        self.code_writer_queue.put("D=M-D")
        self.code_writer_queue.put("@labelTrue" + str(self.index))
        self.code_writer_queue.put("D;" + jmp)
        self.code_writer_queue.put("D=0")
        self.code_writer_queue.put("@labelFalse" + str(self.index))
        self.code_writer_queue.put("0;JMP")
        self.code_writer_queue.put("(labelTrue" + str(self.index) + ")")
        self.code_writer_queue.put("D=-1")
        self.code_writer_queue.put("(labelFalse" + str(self.index) + ")")
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("A=M")
        self.code_writer_queue.put("M=D")
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("M=M+1")
        self.code_writer_queue.put("\n")

        self.index += 1
        
    def _neg_not_template(self, cmd, operation):
        """
        Template that works for neg and not command
        
        Args:
            cmd (string): for comment, to indicate the operation of hack assembly language produced
            operation (string): the operation distinguish neg from not. neg : -M, not : !M

        """
        self.code_writer_queue.put("//" + cmd)
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("A=M")
        self.code_writer_queue.put("A=A-1")
        self.code_writer_queue.put("M=" + operation)
        self.code_writer_queue.put("\n")

    def _and_or_template(self, cmd, operation):
        """
        Template that works for and & or command

        Args:
            cmd (string): for comment, to indicate the operation of hack assembly language produced
            operation (string): the operation distinguish and from or. and : D&M, not : D|M

        """
        self.code_writer_queue.put("//" + cmd)
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("AM=M-1")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("A=A-1")
        self.code_writer_queue.put("M=" + operation)
        self.code_writer_queue.put("\n")
 
    def _add_sub_template(self, cmd, operation):
        self.code_writer_queue.put("//" + cmd)
        self.code_writer_queue.put("@SP")
        self.code_writer_queue.put("AM=M-1")
        self.code_writer_queue.put("D=M")
        self.code_writer_queue.put("A=A-1")
        self.code_writer_queue.put("M=" + operation)
        self.code_writer_queue.put("\n")

    def _end_template(self):
        """
        Template that works for end command.

        Infinite loop between line @end and 0;JMP to lock the pointer
        """

        self.code_writer_queue.put("//end")
        self.code_writer_queue.put("(END)")
        self.code_writer_queue.put("@END")
        self.code_writer_queue.put("0;JMP")

    def _print_queue(self):
        while not self.code_writer_queue.empty():
            item = self.code_writer_queue.get()
            print(item)
        
if __name__ == "__main__":
        
        cw = Codewriter()
        cw.push_operation("constant", "7")
        

        cw._print_queue()