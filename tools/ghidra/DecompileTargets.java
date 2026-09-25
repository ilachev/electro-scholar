// Decompile functions containing the segmented addresses passed as script arguments.
// @category LegacyTEST

import java.util.LinkedHashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

public class DecompileTargets extends GhidraScript {
    @Override
    public void run() throws Exception {
        Set<Function> functions = new LinkedHashSet<>();
        for (String argument : getScriptArgs()) {
            Address address = toAddr(argument);
            Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
            if (function == null) {
                Instruction instruction = currentProgram.getListing().getInstructionAt(address);
                if (instruction == null && !disassemble(address)) {
                    println("DISASSEMBLY FAILED AT " + address);
                    continue;
                }
                function = createFunction(address, null);
            }
            if (function == null) {
                println("NO FUNCTION AT " + address);
            }
            else {
                functions.add(function);
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (Function function : functions) {
            println("\nDECOMPILE " + function.getEntryPoint() + " " + function.getName());
            DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
            if (result.decompileCompleted()) {
                println(result.getDecompiledFunction().getC());
            }
            else {
                println("FAILED: " + result.getErrorMessage());
            }
        }
        decompiler.dispose();
    }
}
