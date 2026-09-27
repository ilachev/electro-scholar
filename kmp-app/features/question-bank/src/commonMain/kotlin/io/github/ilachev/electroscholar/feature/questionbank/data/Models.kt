package io.github.ilachev.electroscholar.feature.questionbank.data

internal data class Source(
    val id: Long,
    val fileName: String,
    val questionCount: Long,
) {
    val displayName: String = fileName.substringBeforeLast('.')
}

internal data class Topic(
    val id: Long,
    val sourceId: Long,
    val position: Long,
    val questionCount: Long,
    val name: String,
)

internal data class QuestionSummary(
    val id: Long,
    val sourceIndex: Long,
    val number: Long,
    val text: String,
    val imageFile: String?,
    val answerMask: Long,
    val warnings: String,
)

internal data class Answer(
    val position: Long,
    val text: String,
    val isExpected: Boolean,
)

internal data class QuestionDetail(
    val id: Long,
    val number: Long,
    val label: String,
    val text: String,
    val hint1: String,
    val hint2: String,
    val imageFile: String?,
    val answerMask: Long,
    val warnings: String,
    val topicName: String,
    val sourceFile: String,
    val answers: List<Answer>,
)
