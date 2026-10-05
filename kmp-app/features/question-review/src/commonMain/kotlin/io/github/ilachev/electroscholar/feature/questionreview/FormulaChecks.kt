package io.github.ilachev.electroscholar.feature.questionreview

private val forbiddenLatexCommands = listOf(
    "\\input",
    "\\include",
    "\\write",
    "\\openout",
    "\\read",
    "\\catcode",
    "\\csname",
    "\\newcommand",
    "\\def",
    "\\usepackage",
    "\\documentclass",
    "\\begin",
    "\\end",
    "\\href",
    "\\url",
)

internal fun candidateIssues(node: ReviewNode, candidate: String): List<String> = buildList {
    if (node.editable && candidate.isBlank()) {
        add("Значение не может быть пустым")
    }
    if (node.kind == ReviewNodeKind.Formula) {
        var balance = 0
        candidate.forEach { character ->
            when (character) {
                '{' -> balance += 1
                '}' -> balance -= 1
            }
            if (balance < 0) return@forEach
        }
        if (balance != 0) add("Фигурные скобки LaTeX не сбалансированы")
        forbiddenLatexCommands.firstOrNull { it in candidate }?.let {
            add("Команда $it запрещена в формулах")
        }
    }
}
