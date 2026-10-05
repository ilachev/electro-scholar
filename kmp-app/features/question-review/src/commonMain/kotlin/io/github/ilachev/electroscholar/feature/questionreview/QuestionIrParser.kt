package io.github.ilachev.electroscholar.feature.questionreview

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

private val questionIrJson = Json {
    ignoreUnknownKeys = true
}

@Serializable
private data class QuestionIr(
    @SerialName("schema_version") val schemaVersion: String,
    @SerialName("document_id") val documentId: String,
    @SerialName("source_record") val sourceRecord: SourceRecordIr,
    val assets: List<AssetIr>,
    val prompt: List<ContentNodeIr>,
    val answers: List<ContainerIr>,
    val hints: List<ContainerIr>,
    @SerialName("answer_key") val answerKey: AnswerKeyIr,
    val verification: VerificationIr,
)

@Serializable
private data class SourceRecordIr(
    @SerialName("source_file") val sourceFile: String,
    @SerialName("source_index") val sourceIndex: Long,
    @SerialName("question_number") val questionNumber: Long,
)

@Serializable
private data class AssetIr(
    val role: String,
    val uri: String,
    val width: Int,
    val height: Int,
)

@Serializable
private data class ContainerIr(
    val id: String,
    val position: Int,
    @SerialName("review_status") val reviewStatus: String,
    val content: List<ContentNodeIr>,
)

@Serializable
private data class ContentNodeIr(
    val id: String,
    val kind: String,
    val text: String? = null,
    val latex: String? = null,
    @SerialName("plain_text") val plainText: String? = null,
    @SerialName("document_ref") val documentRef: String? = null,
    @SerialName("review_status") val reviewStatus: String,
    val evidence: List<EvidenceIr> = emptyList(),
    @SerialName("fallback_bounds") val fallbackBounds: BoundsIr? = null,
)

@Serializable
private data class EvidenceIr(
    val kind: String,
    val bounds: BoundsIr? = null,
)

@Serializable
private data class BoundsIr(
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int,
) {
    fun toSourceBounds() = SourceBounds(x, y, width, height)
}

@Serializable
private data class AnswerKeyIr(
    val id: String,
    val status: String,
    val positions: List<Int>,
)

@Serializable
private data class VerificationIr(
    val status: String,
    val checks: List<VerificationCheckIr>,
)

@Serializable
private data class VerificationCheckIr(
    val id: String,
    val kind: String,
    val status: String,
    val method: String? = null,
)

internal fun parseQuestionIr(input: QuestionReviewInput): ReviewDocument {
    val ir = questionIrJson.decodeFromString<QuestionIr>(input.documentJson)
    require(ir.schemaVersion == "question-ir/v1") {
        "Unsupported Question IR schema: ${ir.schemaVersion}"
    }
    require(ir.sourceRecord.sourceFile == input.sourceFile) {
        "Question IR source file does not match the runtime record"
    }
    require(ir.sourceRecord.sourceIndex == input.sourceIndex) {
        "Question IR source index does not match the runtime record"
    }
    require(ir.sourceRecord.questionNumber == input.questionNumber) {
        "Question IR question number does not match the runtime record"
    }
    val sourceAsset = ir.assets.firstOrNull { it.role == "source" }
        ?: error("Question IR ${ir.documentId} has no source asset")
    require(input.imageFile?.substringAfterLast('/') == sourceAsset.uri.substringAfterLast('/')) {
        "Question IR source image does not match the runtime record"
    }

    val nodes = buildList {
        ir.prompt.forEachIndexed { index, node ->
            add(node.toReviewNode(section = "Условие", label = "Фрагмент ${index + 1}"))
        }
        ir.answers.forEach { answer ->
            answer.content.forEachIndexed { index, node ->
                add(
                    node.toReviewNode(
                        section = "Ответы",
                        label = "Вариант ${answer.position}, фрагмент ${index + 1}",
                    ),
                )
            }
        }
        ir.hints.forEach { hint ->
            hint.content.forEachIndexed { index, node ->
                add(
                    node.toReviewNode(
                        section = "Подсказки",
                        label = "Подсказка ${hint.position}, фрагмент ${index + 1}",
                    ),
                )
            }
        }
        add(
            ReviewNode(
                id = ir.answerKey.id,
                section = "Ключ ответа",
                label = "Правильные позиции",
                kind = ReviewNodeKind.AnswerKey,
                originalValue = ir.answerKey.positions.joinToString(", "),
                originalPlainText = null,
                plainPreview = ir.answerKey.positions.joinToString(", "),
                sourceReviewStatus = ir.answerKey.status,
                bounds = null,
            ),
        )
    }

    return ReviewDocument(
        documentId = ir.documentId,
        schemaVersion = ir.schemaVersion,
        questionId = input.questionId,
        questionNumber = input.questionNumber,
        sourceFile = input.sourceFile,
        sourceIndex = input.sourceIndex,
        imageFile = input.imageFile,
        imageWidth = sourceAsset.width,
        imageHeight = sourceAsset.height,
        verificationStatus = ir.verification.status,
        nodes = nodes,
        checks = ir.verification.checks.map {
            VerificationCheck(it.id, it.kind, it.status, it.method)
        },
    )
}

private fun ContentNodeIr.toReviewNode(section: String, label: String): ReviewNode {
    val nodeKind = when (kind) {
        "text" -> ReviewNodeKind.Text
        "formula" -> ReviewNodeKind.Formula
        "circuit" -> ReviewNodeKind.Circuit
        else -> error("Unsupported Question IR content kind: $kind")
    }
    val value = when (nodeKind) {
        ReviewNodeKind.Text -> text.orEmpty()
        ReviewNodeKind.Formula -> latex.orEmpty()
        ReviewNodeKind.Circuit -> documentRef.orEmpty()
        ReviewNodeKind.AnswerKey -> error("Answer keys are not content nodes")
    }
    return ReviewNode(
        id = id,
        section = section,
        label = label,
        kind = nodeKind,
        originalValue = value,
        originalPlainText = if (nodeKind == ReviewNodeKind.Formula) plainText.orEmpty() else null,
        plainPreview = plainText ?: text ?: documentRef.orEmpty(),
        sourceReviewStatus = reviewStatus,
        bounds = evidence.firstNotNullOfOrNull { it.bounds }?.toSourceBounds()
            ?: fallbackBounds?.toSourceBounds(),
    )
}
