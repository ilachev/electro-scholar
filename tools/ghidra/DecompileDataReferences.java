// Decompile functions that reference the segmented data addresses passed as arguments.
// @category LegacyTEST

import java.util.LinkedHashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class DecompileDataReferences extends GhidraScript {
    @Override
    public void run() throws Exception {
        Set<Function> functions = new LinkedHashSet<>();
        for (String argument : getScriptArgs()) {
            Address target = toAddr(argument);
            println("\nREFERENCES TO " + target);
            for (Reference reference : currentProgram.getReferenceManager().getReferencesTo(target)) {
                Address from = reference.getFromAddress();
                Function function = currentProgram.getFunctionManager().getFunctionContaining(from);
                println(
                    "  " + from + " " + reference.getReferenceType() +
                    (function == null ? "" : " in " + function.getEntryPoint())
                );
                if (function != null) {
                    functions.add(function);
                }
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
