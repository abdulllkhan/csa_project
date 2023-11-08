import os
import argparse

MemSize = 1000 # memory size, in reality, the memory size should be 2^32, but for this lab, for the space reason, we keep it as this large number, but the memory is still 32-bit addressable.

def convertToBinary(n, bits):
    s = bin(n & int("1" * bits, 2))[2: ]
    return ("{0:0>%s}" % (bits)).format(s)

def twosComplimentOfBinary(bin, digit):
        while len(bin) < digit:
            bin = '0' + bin
        if bin[0] == '0':
            return int(bin, 2)
        else:
            return -1 * (int(''.join('1' if x == '0' else '0' for x in bin), 2) + 1)

class InsMem(object):
    def __init__(self, name, ioDir, outputDir):
        self.id = name
        os.path.join(ioDir,"input")
        with open(ioDir + "/imem.txt") as im:
            self.IMem = [data.replace("\n", "") for data in im.readlines()]

    def readInstr(self, ReadAddress):
        # read instruction memory
        # return 32 bit hex val
        address = ReadAddress - (ReadAddress % 4)
        return "".join(self.IMem[address:address+4])
          
class DataMem(object):
    def __init__(self, name, ioDir, dir2):
        self.id = name
        self.ioDir = ioDir
        self.dir2 = dir2
        with open(ioDir + "/dmem.txt") as dm:   #os.path.join not working
            self.DMem = [data.replace("\n", "") for data in dm.readlines()]
        self.DMem.extend(['00000000' for i in range(MemSize-len(self.DMem))])
    
    def readDataMem(self, ReadAddress):
        #read data memory
        #return 32 bit hex val
        address = ReadAddress - (ReadAddress % 4)
        return int("".join(self.DMem[address: address + 4]), 2)
        
    def writeDataMem(self, Address, WriteData):
        # write data into byte addressable memory
        WriteData = convertToBinary(WriteData,32)
        newAddress = Address - ( Address % 4 )
        for i in range(4):
            self.DMem[newAddress + i] = WriteData[8 * i: 8 * i + 8]
        pass # not required even if there is no return statement
                     
    def outputDataMem(self):
        # resPath = os.path.join(self.ioDir, f"{self.id}_DMEMResult.txt")
        resPath = os.path.join(self.dir2)
        resPath = os.path.join(resPath, self.id + "_DMEMResult.txt")
        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])

class RegisterFile(object):
    def __init__(self, outputDir):
        self.outputFile = os.path.join(outputDir, "SS_" + "RFResult.txt")
        # self.Registers = [0x0 for i in range(32)]
        self.Registers = ["".join(["0" for x in range(32)]) for i in range(32)]
    
    def readRF(self, Reg_addr):
        # Fill in
        return int(self.Registers[Reg_addr], 2)
        # pass
    
    def writeRF(self, Reg_addr, Wrt_reg_data):
        # Fill in
        if Reg_addr == 0:
            return
        self.Registers[Reg_addr] = convertToBinary(Wrt_reg_data, 32)
        pass
         
    def outputRF(self, cycle):
        op = ["-" * 70 + "\n", "State of RF after executing cycle:" + str(cycle) + "\n"]
        op.extend([str(val) + "\n" for val in self.Registers])
        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.outputFile, perm) as file:
            file.writelines(op)

class State(object):
    def __init__(self):
        self.IF = {"nop": True, "PC": 0}
        self.ID = {"nop": True, "Instr": 0}
        self.EX = {"nop": True, "Read_data1": 0, "Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "is_I_type": False, "rd_mem": 0,
                   "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0}
        self.MEM = {"nop": True, "ALUresult": 0, "Store_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "rd_mem": 0,
                   "wrt_mem": 0, "wrt_enable": 0}
        self.WB = {"nop": True, "Wrt_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "wrt_enable": 0}

class Core(object):
    def __init__(self, ioDir, outputDir, imem, dmem):
        self.myRF = RegisterFile(outputDir)
        self.cycle = 0
        self.halted = False
        self.ioDir = ioDir
        self.outputDir = outputDir
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem
        self.state.IF["nop"] = False
        self.regPipeline = registerPipeline()
        self.checkHazards = checkHazards()

class SingleStageCore(Core):
    def __init__(self, ioDir, outputDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir + "/SS_", outputDir, imem, dmem)
        # self.opFilePath = os.path.join(outputDir, "StateResult_SS.txt")
        self.opFilePath = outputDir + "/StateResult_SS.txt"

    def writeBack(self):
        if not self.state.WB["nop"]:
            if self.state.WB["registerWrite"]:
                Reg_addr = self.state.WB["Wrt_reg_addr"]
                if self.state.EX["memReg"]:
                    Wrt_reg_data = self.state.MEM["Wrt_data"]
                else:
                    Wrt_reg_data = self.state.MEM["ALUresult"]
                self.myRF.writeRF(Reg_addr,Wrt_reg_data)

    def loadStore(self):
        self.state.WB["nop"] = self.state.MEM["nop"]
        if not self.state.MEM["nop"]:
            if self.state.MEM["wrt_mem"]:
                writeData = self.state.EX["Read_data2"]
                writeAddress = self.state.MEM["ALUresult"]
                self.ext_dmem.writeDataMem(writeAddress,writeData)
            
            if self.state.MEM["rd_mem"]:
                readAddress = self.state.MEM["ALUresult"]
                self.state.MEM["Wrt_data"] = self.ext_dmem.readDataMem(readAddress)
            self.state.MEM["Wrt_reg_addr"] = self.state.EX["Wrt_reg_addr"]
                
            self.state.WB["registerWrite"] = self.state.EX["registerWrite"]
            self.state.WB["Wrt_reg_addr"] = self.state.MEM["Wrt_reg_addr"]
        else:
            self.state.WB["nop"] = True

    def instructionExecute(self):
        self.state.MEM["nop"] = self.state.EX["nop"]
        if not self.state.EX["nop"]:
            if self.state.EX["imm"] != "X":
                op2 = self.state.EX["imm"]
            else:
                op2 = self.state.EX["Read_data2"]
            #addition
            if self.state.EX["aluControl"] == "0010":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] + op2
            #subtraction
            if self.state.EX["aluControl"] == "0110":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] - op2
            #and operation
            if self.state.EX["aluControl"] == "0000":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] & op2
            #or operation
            if self.state.EX["aluControl"] == "0001":
                self.state.MEM["ALUresult"]=self.state.EX["Read_data1"] | op2
            #xor operation
            if self.state.EX["aluControl"] == "0011":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] ^ op2
            #branch
            if self.state.EX["branch"]:
                if self.state.EX["func3"] == "000" and self.state.MEM["ALUresult"] == 0:
                    self.nextState.IF["PC"] = self.state.IF["PC"] + (self.state.EX["pcJump"])
                    self.nextState.IF["nop"] = False
                    self.state.MEM["nop"] = True
                elif self.state.EX["func3"] == "001" and self.state.MEM["ALUresult"] != 0:
                    self.nextState.IF["PC"] = self.state.IF["PC"] + (self.state.EX["pcJump"])
                    self.nextState.IF["nop"] = False
                    self.state.MEM["nop"] = True
                elif self.state.EX["func3"] == "X" :
                    self.nextState.IF["nop"] = False
                    self.nextState.IF["PC"] = self.state.IF["PC"] + (self.state.EX["pcJump"])
            self.state.MEM["rd_mem"] = self.state.EX["rd_mem"]
            self.state.MEM["wrt_mem"] = self.state.EX["wrt_mem"]

    def instructionDecode(self):
        self.state.EX["nop"] = self.state.ID["nop"]
        if not self.state.ID["nop"]:
            
            instructionReverse = self.state.ID["Instr"][::-1]
            opcode = instructionReverse[0:7]
            
            #R-type instruction
            if opcode == "1100110":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                rd = instructionReverse[7:12][::-1]
                func7 = instructionReverse[25:32][::-1]
                func3 = instructionReverse[12:15][::-1] + func7[1]
                aluContol = {"0000":"0010", "0001":"0110", "1110":"0000", "1100":"0001", "1000":"0011"}
                self.state.EX = {
                                    "nop": False, 
                                    "Read_data1": self.myRF.readRF(int(rs1, 2)), 
                                    "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                    "imm": "X", 
                                    "Rs": 0, 
                                    "Rt": 0, 
                                    "pcJump": 0,
                                    "is_I_type": False, 
                                    "rd_mem": 0, 
                                    "aluSource": 0, 
                                    "aluControl": aluContol[func3], 
                                    "alu_op": "10",
                                    "Wrt_reg_addr": int(rd, 2), 
                                    "wrt_mem": 0, 
                                    "registerWrite": 1, 
                                    "branch": 0, 
                                    "memReg": 0
                                }
                
            #I-type instruction
            if opcode == "1100100":
                rs1 = instructionReverse[15:20][::-1]
                imm = instructionReverse[20:32][::-1]
                rd = instructionReverse[7:12][::-1]
                func3 = instructionReverse[12:15][::-1]
                aluContol = {"000":"0010", "111":"0000", "110":"0001", "100":"0011"}
                self.state.EX = {
                                    "nop": False, 
                                    "Read_data1": self.myRF.readRF(int(rs1, 2)), 
                                    "Read_data2": 0,
                                    "imm": twosComplimentOfBinary(imm, 12), 
                                    "Rs": 0, 
                                    "Rt": 0, 
                                    "pcJump": 0,
                                    "is_I_type": True, 
                                    "rd_mem": 0, 
                                    "aluSource": 1, 
                                    "aluControl": aluContol[func3], 
                                    "alu_op": "00",
                                    "Wrt_reg_addr": int(rd, 2), 
                                    "wrt_mem": 0, 
                                    "registerWrite": 1,
                                    "branch": 0,
                                    "memReg": 0
                                }
            
            #I-type instruction
            if opcode == "1100000":
                rs1 = instructionReverse[15:20][::-1]
                imm = instructionReverse[20:32][::-1]
                rd = instructionReverse[7:12][::-1]
                self.state.EX = {
                                    "nop": False, 
                                    "Read_data1": self.myRF.readRF(int(rs1,2)), 
                                    "Read_data2": 0,
                                    "imm":twosComplimentOfBinary(imm,12), 
                                    "Rs": 0, 
                                    "Rt": 0, 
                                    "pcJump": 0,
                                    "is_I_type": False, 
                                    "rd_mem": 1, 
                                    "aluSource":1, 
                                    "aluControl":"0010", 
                                    "alu_op": "00",
                                    "Wrt_reg_addr": int(rd,2), 
                                    "wrt_mem": 0, 
                                    "registerWrite": 1, 
                                    "branch":0, 
                                    "memReg":1
                                }
            
            #S-type instruction
            if opcode == "1100010":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                imm = instructionReverse[7:12] + instructionReverse[25:32]
                imm = imm[::-1] # reversing immediate
                self.state.EX = {
                                    "nop": False,  
                                    "Read_data1": self.myRF.readRF(int(rs1, 2)), 
                                    "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                    "imm": int(imm, 2), 
                                    "Rs": 0, 
                                    "Rt": 0, 
                                    "pcJump": 0,
                                    "is_I_type": False, 
                                    "rd_mem": 0, 
                                    "aluSource": 1, 
                                    "aluControl": "0010", 
                                    "alu_op": "00",
                                    "Wrt_reg_addr": "X", 
                                    "wrt_mem": 1, 
                                    "registerWrite": 0, 
                                    "branch": 0, 
                                    "memReg": "X"
                                }
           
            #SB-type instruction
            if opcode == "1100011":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                imm = "0" + instructionReverse[8:12] + instructionReverse[25:31] + instructionReverse[7] + instructionReverse[31]#check
                imm = imm[::-1]  # reversing immediate
                func3 = instructionReverse[12:15][::-1]
                self.state.EX = {
                                    "nop": False, 
                                    "Read_data1": self.myRF.readRF(int(rs1, 2)), 
                                    "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                    "imm": "X", 
                                    "Rs": 0, 
                                    "Rt": 0, 
                                    "pcJump": twosComplimentOfBinary(imm, 13),
                                    "is_I_type": False, 
                                    "rd_mem": 0, 
                                    "aluSource": 0, 
                                    "aluControl": "0110", 
                                    "alu_op": "01",
                                    "Wrt_reg_addr": "X", 
                                    "wrt_mem": 0,  
                                    "registerWrite": 0, 
                                    "branch": 1, 
                                    "memReg": "X", 
                                    "func3": func3
                                }
            
            #UJ-type instruction
            if opcode == "1111011":
                rs1 = instructionReverse[15:20][::-1]
                rd = instructionReverse[7:12][::-1]
                imm = "0" + instructionReverse[21:31] + instructionReverse[20] + instructionReverse[12:20]  + instructionReverse[31] #check
                imm = imm[::-1]
                self.state.EX = {
                                    "nop" : False, 
                                    "Read_data1" : self.state.IF['PC'], 
                                    "Read_data2" : 4, 
                                    "imm":"X", "Rs" : 0, 
                                    "Rt" : 0, 
                                    "pcJump" : twosComplimentOfBinary(imm,21), 
                                    "is_I_type" : False, 
                                    "rd_mem" : 0, 
                                    "aluSource" :1, 
                                    "aluControl" :"0010", 
                                    "alu_op" : "10", 
                                    "Wrt_reg_addr" : int(rd,2), 
                                    "wrt_mem" : 0, 
                                    "registerWrite" : 1, 
                                    "branch" :1, 
                                    "memReg" :0, 
                                    "func3" :"X"
                                }
                
    def instructionFetch(self):
        self.state.ID["Instr"] = self.ext_imem.readInstr(self.state.IF["PC"])
        instructionReverse = self.state.ID["Instr"][::-1]
        opcode = instructionReverse[0:7]
        if opcode=="1111111":
            self.nextState.IF["PC"] = self.state.IF["PC"]
            self.nextState.IF["nop" ] = True
        else:
            self.nextState.IF["nop"] = False
            self.nextState.IF["PC"] = self.state.IF["PC"] + 4
            self.state.ID["nop"] = False

    def step(self):
        # Your implementation
        self.instructionFetch()
        self.instructionDecode()
        self.instructionExecute()
        self.loadStore()
        self.writeBack()



        # self.halted = True
        if self.state.IF["nop"]:
            self.halted = True
            
        self.myRF.outputRF(self.cycle) # dump RF
        self.printState(self.nextState, self.cycle) # print states after executing cycle 0, cycle 1, cycle 2 ...       
        self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
        self.nextState = State()  # is this necessary?
        self.cycle += 1
        return self.cycle

    def printState(self, state, cycle):
        printstate = ["-" * 70 + "\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")
        
        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

class registerPipeline(object):
    def __init__(self):
        self.IF_ID = {"PC": 0, "rawInstruction": 0}
        self.ID_EX = {"PC": 0, "instruction": 0, "rs": 0, "rt": 0}
        self.EX_MEM = {"PC": 0, "instruction": 0,  "ALUresult": 0, "rt": 0}
        self.MEM_WB = {"PC": 0, "instruction": 0,  "Wrt_data": 0, "ALUresult": 0, "rt": 0}

class PerformanceMetrics(Core):
    def __init__(self, ioDir, dir2, ss_cycle):
        self.newFile = open(dir2 + "/PerformanceMetrics_Result.txt", "w")
        self.newFile.write("Single Stage Core Performance Metrics-----------------------------\n")
        self.newFile.write("Number of cycles taken: " + str(ss_cycle) + "\n")
        with open(ioDir + "/imem.txt", "r") as fp:
            x = len(fp.readlines())
            x = x / 4
            
        ss_CPI = ss_cycle / x
        ss_CPI = round(ss_CPI, 5)
        self.newFile.write("Cycles per instruction: " + str(ss_CPI) + "\n")
        ss_IPC = 1 / ss_CPI
        ss_IPC = round(ss_IPC, 6)
        self.newFile.write("Instructions per cycle: " + str(ss_IPC) + "\n")
        self.newFile.write("Instructions: " + str(x) + "\n")

class checkHazards():
    def hazardRegWrite(self, pr:registerPipeline, rs):  # hazard check memory write-back stage
        return  rs != 0 and pr.MEM_WB["instruction"]  \
                and pr.MEM_WB["instruction"]["registerWrite"] \
                and pr.MEM_WB["instruction"]["Wrt_reg_addr"] == rs
    def hazardLoad(self, pr:registerPipeline, rs1, rs2):  # load instruction hazards check. checks if rs1 and rs2 are similar to rd_mem
        return pr.ID_EX["instruction"] \
                and pr.ID_EX["instruction"]["rd_mem"] \
                and (pr.ID_EX["instruction"]["Wrt_reg_addr"] == int(rs1, 2) or pr.ID_EX["instruction"]["Wrt_reg_addr"] == int(rs2, 2))
    def hazardMEM(self, pr:registerPipeline, rs): # memory stage hazards check related to register writes
        return  pr.MEM_WB["instruction"] \
                and pr.MEM_WB["instruction"]["registerWrite"] \
                and pr.MEM_WB["instruction"]["Wrt_reg_addr"] != 0 \
                and pr.MEM_WB["instruction"]["Wrt_reg_addr"] == rs
    def hazardEX(self,pr:registerPipeline, rs):  # execute stage hazard check related to register writes
        return  pr.EX_MEM["instruction"] \
                and pr.EX_MEM["instruction"]["registerWrite"] \
                and not pr.EX_MEM["instruction"]["rd_mem"] \
                and pr.EX_MEM["instruction"]["Wrt_reg_addr"] != 0 \
                and pr.EX_MEM["instruction"]["Wrt_reg_addr"] == rs

class FiveStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(FiveStageCore, self).__init__(os.path.join(ioDir, "FS_"), imem, dmem)
        self.opFilePath = os.path.join(ioDir, "StateResult_FS.txt")

    def step(self):
        # Your implementation
        # --------------------- WB stage ---------------------
        
        
        
        # --------------------- MEM stage --------------------
        
        
        
        # --------------------- EX stage ---------------------
        
        
        
        # --------------------- ID stage ---------------------
        
        
        
        # --------------------- IF stage ---------------------
        
        self.halted = True
        if self.state.IF["nop"] and self.state.ID["nop"] and self.state.EX["nop"] and self.state.MEM["nop"] and self.state.WB["nop"]:
            self.halted = True
        
        self.myRF.outputRF(self.cycle) # dump RF
        self.printState(self.nextState, self.cycle) # print states after executing cycle 0, cycle 1, cycle 2 ... 
        
        self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
        self.cycle += 1

    def printState(self, state, cycle):
        printstate = ["-"*70+"\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.extend(["IF." + key + ": " + str(val) + "\n" for key, val in state.IF.items()])
        printstate.extend(["ID." + key + ": " + str(val) + "\n" for key, val in state.ID.items()])
        printstate.extend(["EX." + key + ": " + str(val) + "\n" for key, val in state.EX.items()])
        printstate.extend(["MEM." + key + ": " + str(val) + "\n" for key, val in state.MEM.items()])
        printstate.extend(["WB." + key + ": " + str(val) + "\n" for key, val in state.WB.items()])

        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

if __name__ == "__main__":

    ioDir_main = os.path.abspath("input/")

    if os.path.exists(ioDir_main):

        folders = [f for f in os.listdir(ioDir_main) if os.path.isdir(os.path.join(ioDir_main, f))]

        for testdir in folders:
            ioDir = os.path.join(ioDir_main,testdir)
            print("IO Directory:", ioDir)
            
            dir1 = os.path.dirname(os.path.dirname(ioDir))
            fname = os.path.basename(ioDir)
            dir2 = os.path.join(dir1, "output_ak9943")
            
            if not os.path.exists(dir2):
                os.makedirs(dir2)
            
            dir2 = os.path.join(dir2, fname)
            
            if not os.path.exists(dir2):
                os.makedirs(dir2)
            
            imem = InsMem("Imem", ioDir, dir2)
            dmem_ss = DataMem("SS", ioDir, dir2)
    
            ssCore = SingleStageCore(ioDir, dir2, imem, dmem_ss)
            
            while(True):
                if not ssCore.halted:
                    ss_cycle = ssCore.step()
                    
                if ssCore.halted: # not really needed
                    break

            PerformanceMetrics(ioDir, dir2, ss_cycle)
            dmem_ss.outputDataMem()   
     
    # # parse arguments for input file location
    # parser = argparse.ArgumentParser(description='RV32I processor')
    # parser.add_argument('--iodir', default="", type=str, help='Directory containing the input files.')
    # args = parser.parse_args()

    # ioDir = os.path.abspath(args.iodir)
    # print("IO Directory:", ioDir)

    # imem = InsMem("Imem", ioDir)
    # dmem_ss = DataMem("SS", ioDir)
    # dmem_fs = DataMem("FS", ioDir)
    
    # ssCore = SingleStageCore(ioDir, imem, dmem_ss)
    # fsCore = FiveStageCore(ioDir, imem, dmem_fs)

    # while(True):
    #     if not ssCore.halted:
    #         ssCore.step()
        
    #     if not fsCore.halted:
    #         fsCore.step()

    #     if ssCore.halted and fsCore.halted:
    #         break
    
    # # dump SS and FS data mem.
    # dmem_ss.outputDataMem()
    # dmem_fs.outputDataMem()
