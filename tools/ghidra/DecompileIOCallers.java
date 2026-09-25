// Decompile functions that directly call Win16 file and memory APIs.
// @category LegacyTEST

import java.util.LinkedHashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class DecompileIOCallers extends GhidraScript {
    private static final Set<String> TARGETS = Set.of(
        "_HREAD",
        "_HWRITE",
        "_LLSEEK",
        "_LCLOSE",
        "GLOBALALLOC",
        "GLOBALLOCK",
        "GLOBALUNLOCK"
    );

    @Override
    public void run() throws Exception {
        Set<Function> callers = new LinkedHashSet<>();
        for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
            if (!TARGETS.contains(function.getName())) {
                continue;
            }
            println("TARGET " + function.getName() + " " + function.getEntryPoint());
            for (Reference reference : currentProgram.getReferenceManager().getReferencesTo(function.getEntryPoint())) {
                Function caller = currentProgram.getFunctionManager().getFunctionContaining(reference.getFromAddress());
                if (caller != null) {
                    println("  CALLER " + caller.getEntryPoint() + " via " + reference.getFromAddress());
                    callers.add(caller);
                }
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (Function caller : callers) {
            println("\nDECOMPILE " + caller.getEntryPoint() + " " + caller.getName());
            DecompileResults result = decompiler.decompileFunction(caller, 60, monitor);
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
