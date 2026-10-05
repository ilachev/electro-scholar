package io.github.ilachev.electroscholar.feature.questionbank.data

import io.github.ilachev.electroscholar.feature.questionbank.loadStructuredQuestionDocuments
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull

class DatabaseSmokeTest {
    @Test
    fun readsAllSourcesAndTopics() = runTest {
        val repository = QuestionRepository(createDatabase())
        val sources = repository.sources()
        assertEquals(listOf(265L, 317L), sources.map { it.questionCount })
        assertEquals(5, repository.topics(sources.first().id).size)
        assertEquals(5, repository.topics(sources.last().id).size)
    }

    @Test
    fun readsQuestionAndExpectedAnswer() = runTest {
        val repository = QuestionRepository(createDatabase())
        val source = repository.sources().first()
        val topic = repository.topics(source.id).first()
        val summary = repository.questions(topic.id, "").first()
        val question = assertNotNull(repository.question(summary.id))

        assertEquals(1L, question.number)
        assertEquals(5L, question.answers.single { it.isExpected }.position)
        assertNotNull(question.imageFile)
    }

    @Test
    fun filtersQuestionsAndPreservesKnownSourceDefect() = runTest {
        val repository = QuestionRepository(createDatabase())
        val source = repository.sources().last()
        val topic = repository.topics(source.id)[1]
        val matches = repository.questions(topic.id, "121")

        assertEquals(1, matches.size)
        val question = assertNotNull(repository.question(matches.single().id))
        assertEquals(121L, question.number)
        assertEquals("missing_correct_answer", question.warnings)
        assertEquals(0, question.answers.count { it.isExpected })
    }

    @Test
    fun keepsUnverifiedQuestionIrBehindThePublicationGate() = runTest {
        val database = createDatabase()
        val repository = QuestionRepository(database)
        val source = repository.sources().last()
        val topic = repository.topics(source.id).first()
        val unpublishedMatches = repository.questions(topic.id, "эквивалентным")
        val matches = repository.questions(topic.id, "19")

        assertEquals(1L, repository.structuredDocumentCount())
        assertEquals(0, unpublishedMatches.size)
        assertEquals(1, matches.size)
        val question = assertNotNull(repository.question(matches.single().id))
        assertEquals(19L, question.number)
        assertEquals("in_review", question.structuredReviewStatus)
        assertEquals("уКАЖИТЕ НОМЕР ПРАВИЛЬНОГО ОТВЕТА.", question.text)
        assertEquals("", question.answers.single { it.position == 5L }.text)
        assertEquals(5L, question.answers.single { it.isExpected }.position)
        assertEquals(
            21,
            database.databaseQueries.selectContentNodesForQuestion(question.id).executeAsList().size,
        )
    }

    @Test
    fun exposesStructuredDocumentsThroughTheReadOnlyReviewBridge() = runTest {
        val documents = loadStructuredQuestionDocuments()

        assertEquals(1, documents.size)
        assertEquals("legacy-test:test2:018", documents.single().documentId)
        assertEquals("in_review", documents.single().reviewStatus)
        assertEquals(19L, documents.single().questionNumber)
        assertNotNull(documents.single().imageFile)
    }
}
