package io.github.ilachev.electroscholar.feature.questionbank

import io.github.ilachev.electroscholar.feature.questionbank.data.createDatabase

data class StructuredQuestionDocument(
    val questionId: Long,
    val questionNumber: Long,
    val questionLabel: String,
    val sourceIndex: Long,
    val sourceFile: String,
    val imageFile: String?,
    val documentId: String,
    val schemaVersion: String,
    val reviewStatus: String,
    val documentJson: String,
)

suspend fun loadStructuredQuestionDocuments(): List<StructuredQuestionDocument> {
    val database = createDatabase()
    return database.databaseQueries.selectStructuredDocumentsForReview {
            questionId, questionNumber, questionLabel, sourceIndex, sourceFile, imageFile,
            documentId, schemaVersion, reviewStatus, documentJson ->
        StructuredQuestionDocument(
            questionId = questionId,
            questionNumber = questionNumber,
            questionLabel = questionLabel,
            sourceIndex = sourceIndex,
            sourceFile = sourceFile,
            imageFile = imageFile,
            documentId = documentId,
            schemaVersion = schemaVersion,
            reviewStatus = reviewStatus,
            documentJson = documentJson,
        )
    }.executeAsList()
}
