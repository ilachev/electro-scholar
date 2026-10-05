package io.github.ilachev.electroscholar.feature.questionreview.data

import io.github.ilachev.electroscholar.feature.questionreview.DocumentReviewState
import io.github.ilachev.electroscholar.feature.questionreview.ReviewDecision
import io.github.ilachev.electroscholar.feature.questionreview.ReviewEventRecord
import io.github.ilachev.electroscholar.feature.questionreview.ReviewNode
import io.github.ilachev.electroscholar.feature.questionreview.ReviewNodeKind
import io.github.ilachev.electroscholar.feature.questionreview.StoredNodeReview

internal class ReviewRepository(private val database: QuestionReviewDatabase) {
    fun registerDocument(documentId: String, schemaVersion: String, documentJson: String) {
        val existing = database.reviewDatabaseQueries.selectReviewDocument(documentId) {
                storedSchemaVersion, storedDocumentJson ->
            storedSchemaVersion to storedDocumentJson
        }.executeAsOneOrNull()
        if (existing == (schemaVersion to documentJson)) return

        val eventCount = database.reviewDatabaseQueries
            .selectReviewEventCountForDocument(documentId)
            .executeAsOne()
        require(existing == null || eventCount == 0L) {
            "Question IR changed after review events were recorded; export or rebase them first"
        }
        database.reviewDatabaseQueries.upsertReviewDocument(
            document_id = documentId,
            schema_version = schemaVersion,
            base_document_json = documentJson,
        )
    }

    fun state(documentId: String): DocumentReviewState {
        val drafts = database.reviewDatabaseQueries.selectReviewDraftsForDocument(documentId) {
                nodeId, _, _, draftValue, _, draftPlainText ->
            nodeId to (draftValue to draftPlainText)
        }.executeAsList().toMap()

        val events = database.reviewDatabaseQueries.selectReviewEventsForDocument(documentId) {
                id, nodeId, reviewer, decision, comment, originalValue, submittedValue,
                originalPlainText, submittedPlainText, createdAt ->
            ReviewEventRecord(
                id = id,
                nodeId = nodeId,
                reviewer = reviewer,
                decision = ReviewDecision.fromStorage(decision),
                comment = comment,
                originalValue = originalValue,
                submittedValue = submittedValue,
                originalPlainText = originalPlainText,
                submittedPlainText = submittedPlainText,
                createdAt = createdAt,
            )
        }.executeAsList()

        val latestEvents = events.associateBy { it.nodeId }
        val nodeIds = drafts.keys + latestEvents.keys
        val nodes = nodeIds.associateWith { nodeId ->
            val event = latestEvents[nodeId]
            StoredNodeReview(
                draftValue = drafts[nodeId]?.first ?: event?.submittedValue.orEmpty(),
                draftPlainText = drafts[nodeId]?.second ?: event?.submittedPlainText,
                latestDecision = event?.decision,
                reviewer = event?.reviewer,
                comment = event?.comment,
                submittedAt = event?.createdAt,
            )
        }
        return DocumentReviewState(nodes = nodes, events = events)
    }

    fun record(
        documentId: String,
        node: ReviewNode,
        draftValue: String,
        draftPlainText: String?,
        reviewer: String,
        decision: ReviewDecision,
        comment: String,
    ) {
        check(
            database.reviewDatabaseQueries.selectReviewDocument(documentId).executeAsOneOrNull() != null,
        ) { "Review document must be registered before recording decisions" }
        require(reviewer.isNotBlank()) { "Reviewer is required" }
        require(node.kind != ReviewNodeKind.Formula || !draftPlainText.isNullOrBlank()) {
            "Formula plain text is required"
        }
        val changed = draftValue != node.originalValue || draftPlainText != node.originalPlainText
        require(decision != ReviewDecision.Correct || changed) {
            "Correct requires a changed value"
        }
        database.transaction {
            database.reviewDatabaseQueries.upsertReviewDraft(
                document_id = documentId,
                node_id = node.id,
                node_kind = node.kind.name.lowercase(),
                original_value = node.originalValue,
                draft_value = draftValue,
                original_plain_text = node.originalPlainText,
                draft_plain_text = draftPlainText,
            )
            database.reviewDatabaseQueries.insertReviewEvent(
                documentId = documentId,
                nodeId = node.id,
                reviewer = reviewer.trim(),
                decision = decision.storageValue,
                comment = comment.trim(),
                originalValue = node.originalValue,
                submittedValue = draftValue,
                originalPlainText = node.originalPlainText,
                submittedPlainText = draftPlainText,
            )
        }
    }
}
