package io.github.ilachev.electroscholar.feature.questionreview

import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import io.github.ilachev.electroscholar.feature.questionreview.data.QuestionReviewDatabase
import io.github.ilachev.electroscholar.feature.questionreview.data.ReviewRepository
import io.github.ilachev.electroscholar.feature.questionreview.data.initializeReviewSchema
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class QuestionReviewTest {
    private fun input(): QuestionReviewInput {
        val fixture = Files.readString(Path.of(checkNotNull(System.getProperty("questionIrFixture"))))
        return QuestionReviewInput(
            questionId = 283,
            questionNumber = 19,
            sourceFile = "TEST2.DAT",
            sourceIndex = 18,
            imageFile = "images/TEST2_018.jpg",
            documentJson = fixture,
        )
    }

    private fun document(): ReviewDocument = parseQuestionIr(input())

    @Test
    fun parsesRealQuestionIrIntoReviewTargets() {
        val document = document()

        assertEquals("legacy-test:test2:018", document.documentId)
        assertEquals(22, document.nodes.size)
        assertEquals(10, document.nodes.count { it.kind == ReviewNodeKind.Formula })
        assertEquals(1, document.nodes.count { it.kind == ReviewNodeKind.Circuit })
        assertEquals(1, document.nodes.count { it.kind == ReviewNodeKind.AnswerKey })
        assertEquals(SourceBounds(88, 0, 447, 83), document.nodes.first().bounds)
        assertEquals(5, document.checks.size)
    }

    @Test
    fun recordsCorrectionWithoutChangingOriginalValue() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        QuestionReviewDatabase.Schema.create(driver)
        val repository = ReviewRepository(QuestionReviewDatabase(driver))
        val document = document()
        val input = input()
        repository.registerDocument(document.documentId, document.schemaVersion, input.documentJson)
        val formula = document.nodes.first { it.id == "prompt:formula:u0" }
        val corrected = "U_0 = 121\\,\\text{В}"
        val correctedPlainText = "U₀ = 121 В"

        repository.record(
            documentId = document.documentId,
            node = formula,
            draftValue = corrected,
            draftPlainText = correctedPlainText,
            reviewer = "reviewer:test",
            decision = ReviewDecision.Correct,
            comment = "Test correction",
        )

        val state = repository.state(document.documentId)
        val stored = assertNotNull(state.nodes[formula.id])
        assertEquals(corrected, stored.draftValue)
        assertEquals(correctedPlainText, stored.draftPlainText)
        assertEquals(ReviewDecision.Correct, stored.latestDecision)
        assertEquals(formula.originalValue, state.events.single().originalValue)
        assertEquals(corrected, state.events.single().submittedValue)
        assertEquals(formula.originalPlainText, state.events.single().originalPlainText)
        assertEquals(correctedPlainText, state.events.single().submittedPlainText)
    }

    @Test
    fun refusesToReplaceReviewedBaseDocument() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        QuestionReviewDatabase.Schema.create(driver)
        val repository = ReviewRepository(QuestionReviewDatabase(driver))
        val document = document()
        val input = input()
        val node = document.nodes.first()
        repository.registerDocument(document.documentId, document.schemaVersion, input.documentJson)
        repository.record(
            documentId = document.documentId,
            node = node,
            draftValue = node.originalValue,
            draftPlainText = node.originalPlainText,
            reviewer = "reviewer:test",
            decision = ReviewDecision.Accept,
            comment = "",
        )

        kotlin.test.assertFailsWith<IllegalArgumentException> {
            repository.registerDocument(
                document.documentId,
                document.schemaVersion,
                input.documentJson + " ",
            )
        }
    }

    @Test
    fun migratesLegacyDesktopSchemaToDocumentSnapshots() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        driver.execute(
            null,
            "CREATE TABLE review_drafts (" +
                "document_id TEXT NOT NULL, node_id TEXT NOT NULL, node_kind TEXT NOT NULL, " +
                "original_value TEXT NOT NULL, draft_value TEXT NOT NULL, " +
                "PRIMARY KEY(document_id, node_id))",
            0,
        )
        driver.execute(
            null,
            "CREATE TABLE review_events (" +
                "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL, " +
                "node_id TEXT NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL, " +
                "comment TEXT NOT NULL, original_value TEXT NOT NULL, " +
                "submitted_value TEXT NOT NULL, created_at TEXT NOT NULL)",
            0,
        )
        driver.execute(
            null,
            "CREATE INDEX review_events_document_idx ON review_events(document_id, id)",
            0,
        )

        initializeReviewSchema(driver)
        val database = QuestionReviewDatabase(driver)
        assertEquals(0L, database.reviewDatabaseQueries.selectReviewEventCount().executeAsOne())
        assertEquals(2L, QuestionReviewDatabase.Schema.version)
        database.reviewDatabaseQueries.upsertReviewDocument(
            "document:test",
            "question-ir/v1",
            "{}",
        )
        assertNotNull(
            database.reviewDatabaseQueries.selectReviewDocument("document:test").executeAsOneOrNull(),
        )
    }

    @Test
    fun rejectsUnsafeOrMalformedLatex() {
        val formula = document().nodes.first { it.kind == ReviewNodeKind.Formula }

        assertTrue(candidateIssues(formula, "R_{1").isNotEmpty())
        assertTrue(candidateIssues(formula, "\\input{secret}").isNotEmpty())
        assertFalse(candidateIssues(formula, "R_1 = 30\\,\\Omega").isNotEmpty())
    }
}
