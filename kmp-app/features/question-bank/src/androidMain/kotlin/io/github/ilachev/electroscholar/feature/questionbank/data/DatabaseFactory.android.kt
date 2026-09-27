package io.github.ilachev.electroscholar.feature.questionbank.data

import android.content.Context
import app.cash.sqldelight.driver.android.AndroidSqliteDriver

private lateinit var applicationContext: Context

fun initializeQuestionBankAndroid(context: Context) {
    applicationContext = context.applicationContext
}

internal actual suspend fun createDatabase(): QuestionBankDatabase {
    check(::applicationContext.isInitialized) {
        "initializeQuestionBankAndroid(context) must be called before QuestionBankFeature()"
    }

    val databaseFile = applicationContext.getDatabasePath(DATABASE_NAME)
    databaseFile.parentFile?.mkdirs()
    databaseFile.writeBytes(packagedDatabaseBytes())

    val driver = AndroidSqliteDriver(
        schema = QuestionBankDatabase.Schema,
        context = applicationContext,
        name = DATABASE_NAME,
    )
    return QuestionBankDatabase(driver)
}
