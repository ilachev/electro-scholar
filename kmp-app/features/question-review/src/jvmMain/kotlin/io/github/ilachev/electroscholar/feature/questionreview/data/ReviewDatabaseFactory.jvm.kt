package io.github.ilachev.electroscholar.feature.questionreview.data

import app.cash.sqldelight.db.QueryResult
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import java.nio.file.Files

internal actual suspend fun createReviewDatabase(): QuestionReviewDatabase {
    val dataDirectory = java.nio.file.Path.of(System.getProperty("user.home"), ".electroscholar")
    Files.createDirectories(dataDirectory)
    val databasePath = dataDirectory.resolve(REVIEW_DATABASE_NAME)
    val driver = JdbcSqliteDriver("jdbc:sqlite:${databasePath.toAbsolutePath()}")
    initializeReviewSchema(driver)
    return QuestionReviewDatabase(driver)
}

internal fun initializeReviewSchema(driver: JdbcSqliteDriver) {
    val schema = QuestionReviewDatabase.Schema
    val declaredVersion = driver.queryLong("PRAGMA user_version")
    val hasLegacyTables = driver.queryLong(
        "SELECT COUNT(*) FROM sqlite_master " +
            "WHERE type = 'table' AND name = 'review_events'",
    ) > 0L
    val currentVersion = when {
        declaredVersion > 0L -> declaredVersion
        hasLegacyTables -> 1L
        else -> 0L
    }
    require(currentVersion <= schema.version) {
        "Review database version $currentVersion is newer than supported version ${schema.version}"
    }
    when {
        currentVersion == 0L -> schema.create(driver)
        currentVersion < schema.version -> schema.migrate(driver, currentVersion, schema.version)
    }
    if (currentVersion != schema.version) {
        driver.execute(null, "PRAGMA user_version = ${schema.version}", 0)
    }
}

private fun JdbcSqliteDriver.queryLong(statement: String): Long =
    executeQuery(
        identifier = null,
        sql = statement,
        mapper = { cursor -> QueryResult.Value(cursor.getLong(0) ?: 0L) },
        parameters = 0,
    ).value
