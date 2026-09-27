package io.github.ilachev.electroscholar.feature.questionbank.data

import io.github.ilachev.electroscholar.feature.questionbank.resources.Res

internal const val DATABASE_NAME = "question-bank.sqlite"

internal suspend fun packagedDatabaseBytes(): ByteArray =
    Res.readBytes("files/database/question_bank.sqlite")

internal expect suspend fun createDatabase(): QuestionBankDatabase
