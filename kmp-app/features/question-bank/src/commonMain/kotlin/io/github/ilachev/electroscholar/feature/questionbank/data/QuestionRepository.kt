package io.github.ilachev.electroscholar.feature.questionbank.data

internal class QuestionRepository(private val database: QuestionBankDatabase) {
    fun sources(): List<Source> =
        database.databaseQueries.selectSources { id, fileName, questionCount ->
            Source(id, fileName, questionCount)
        }.executeAsList()

    fun topics(sourceId: Long): List<Topic> =
        database.databaseQueries.selectTopicsForSource(sourceId) {
                id, rowSourceId, position, questionCount, name ->
            Topic(id, rowSourceId, position, questionCount, name)
        }.executeAsList()

    fun questions(topicId: Long, query: String): List<QuestionSummary> =
        database.databaseQueries.selectQuestionsForTopic(topicId, query.trim()) {
                id, sourceIndex, number, text, imageFile, answerMask, warnings ->
            QuestionSummary(
                id = id,
                sourceIndex = sourceIndex,
                number = number,
                text = text,
                imageFile = imageFile,
                answerMask = answerMask,
                warnings = warnings,
            )
        }.executeAsList()

    fun question(questionId: Long): QuestionDetail? {
        val answers = database.databaseQueries.selectAnswersForQuestion(questionId) {
                position, text, isCorrect ->
            Answer(position, text, isCorrect != 0L)
        }.executeAsList()

        return database.databaseQueries.selectQuestionById(questionId) {
                id, number, label, text, hint1, hint2, imageFile, answerMask,
                warnings, topicName, sourceFile ->
            QuestionDetail(
                id = id,
                number = number,
                label = label,
                text = text,
                hint1 = hint1,
                hint2 = hint2,
                imageFile = imageFile,
                answerMask = answerMask,
                warnings = warnings,
                topicName = topicName.orEmpty(),
                sourceFile = sourceFile,
                answers = answers,
            )
        }.executeAsOneOrNull()
    }
}
