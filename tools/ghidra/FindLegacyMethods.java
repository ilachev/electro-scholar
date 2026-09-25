// Search a Ghidra project for Delphi method-name strings and their references.
// @category LegacyTEST

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

public class FindLegacyMethods extends GhidraScript {
    private static final String[] NEEDLES = {
        "PakPP",
        "UnPakPP",
        "LoadVopros",
        "SaveVopros",
        "ReadVopros",
        "WriteVopros",
        "UrovenData",
        "Dostup"
    };

    @Override
    public void run() throws Exception {
        Memory memory = currentProgram.getMemory();
        println("MEMORY BLOCKS");
        for (MemoryBlock block : memory.getBlocks()) {
            println(block.getName() + " " + block.getStart() + " " + block.getEnd());
        }

        for (String needle : NEEDLES) {
            println("\nSTRING " + needle);
            byte[] bytes = needle.getBytes(StandardCharsets.US_ASCII);
            Address cursor = memory.getMinAddress();
            while (cursor != null) {
                Address match = memory.findBytes(cursor, bytes, null, true, monitor);
                if (match == null) {
                    break;
                }
                println("  found " + match);
                Address pointerAddress = match.subtract(5);
                byte[] pointerBytes = new byte[4];
                memory.getBytes(pointerAddress, pointerBytes);
                println(
                    String.format(
                        "    preceding pointer %s: %02x %02x %02x %02x",
                        pointerAddress,
                        pointerBytes[0] & 0xff,
                        pointerBytes[1] & 0xff,
                        pointerBytes[2] & 0xff,
                        pointerBytes[3] & 0xff
                    )
                );
                for (Reference reference : currentProgram.getReferenceManager().getReferencesFrom(pointerAddress)) {
                    println("    pointer ref " + reference.getToAddress() + " " + reference.getReferenceType());
                }
                for (Reference reference : collectReferencesTo(match)) {
                    println("    ref " + reference.getFromAddress() + " " + reference.getReferenceType());
                }
                cursor = match.next();
            }
        }

    }

    private List<Reference> collectReferencesTo(Address address) {
        List<Reference> result = new ArrayList<>();
        for (Reference reference : currentProgram.getReferenceManager().getReferencesTo(address)) {
            result.add(reference);
        }
        return result;
    }
}
