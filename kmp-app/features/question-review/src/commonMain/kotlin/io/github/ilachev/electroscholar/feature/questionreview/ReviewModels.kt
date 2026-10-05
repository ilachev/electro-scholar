package io.github.ilachev.electroscholar.feature.questionreview

data class QuestionReviewInput(
    val questionId: Long,
    val questionNumber: Long,
    val sourceFile: String,
    val sourceIndex: Long,
    val imageFile: String?,
    val documentJson: String,
)

data class SourceBounds(
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int,
)

enum class ReviewNodeKind {
    Text,
    Formula,
    Circuit,
    AnswerKey,
}

data class ReviewNode(
    val id: String,
    val section: String,
    val label: String,
    val kind: ReviewNodeKind,
    val originalValue: String,
    val originalPlainText: String?,
    val plainPreview: String,
    val sourceReviewStatus: String,
    val bounds: SourceBounds?,
) {
    val editable: Boolean
        get() = kind == ReviewNodeKind.Text || kind == ReviewNodeKind.Formula
}

data class VerificationCheck(
    val id: String,
    val kind: String,
    val status: String,
    val method: String?,
)

data class ReviewDocument(
    val documentId: String,
    val schemaVersion: String,
    val questionId: Long,
    val questionNumber: Long,
    val sourceFile: String,
    val sourceIndex: Long,
    val imageFile: String?,
    val imageWidth: Int,
    val imageHeight: Int,
    val verificationStatus: String,
    val nodes: List<ReviewNode>,
    val checks: List<VerificationCheck>,
)

enum class ReviewDecision(val storageValue: String) {
    Accept("accept"),
    Correct("correct"),
    Reject("reject"),
    Defer("defer");

    companion object {
        fun fromStorage(value: String): ReviewDecision = entries.first { it.storageValue == value }
    }
}

data class StoredNodeReview(
    val draftValue: String,
    val draftPlainText: String?,
    val latestDecision: ReviewDecision?,
    val reviewer: String?,
    val comment: String?,
    val submittedAt: String?,
)

data class ReviewEventRecord(
    val id: Long,
    val nodeId: String,
    val reviewer: String,
    val decision: ReviewDecision,
    val comment: String,
    val originalValue: String,
    val submittedValue: String,
    val originalPlainText: String?,
    val submittedPlainText: String?,
    val createdAt: String,
)

data class DocumentReviewState(
    val nodes: Map<String, StoredNodeReview>,
    val events: List<ReviewEventRecord>,
)
