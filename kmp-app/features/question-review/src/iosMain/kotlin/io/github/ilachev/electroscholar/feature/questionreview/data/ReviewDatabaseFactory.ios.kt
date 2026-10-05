package io.github.ilachev.electroscholar.feature.questionreview.data

import app.cash.sqldelight.driver.native.NativeSqliteDriver

internal actual suspend fun createReviewDatabase(): QuestionReviewDatabase {
    val driver = NativeSqliteDriver(QuestionReviewDatabase.Schema, REVIEW_DATABASE_NAME)
    return QuestionReviewDatabase(driver)
}
