package io.github.ilachev.electroscholar.feature.questionreview.data

import android.content.Context
import app.cash.sqldelight.driver.android.AndroidSqliteDriver

private lateinit var applicationContext: Context

fun initializeQuestionReviewAndroid(context: Context) {
    applicationContext = context.applicationContext
}

internal actual suspend fun createReviewDatabase(): QuestionReviewDatabase {
    check(::applicationContext.isInitialized) {
        "initializeQuestionReviewAndroid(context) must be called before QuestionReviewFeature()"
    }
    val driver = AndroidSqliteDriver(
        schema = QuestionReviewDatabase.Schema,
        context = applicationContext,
        name = REVIEW_DATABASE_NAME,
    )
    return QuestionReviewDatabase(driver)
}
