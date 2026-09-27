package io.github.ilachev.electroscholar.feature.questionbank.data

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import java.nio.file.Files
import java.util.Properties

internal actual suspend fun createDatabase(): QuestionBankDatabase {
    val dataDirectory = java.nio.file.Path.of(System.getProperty("user.home"), ".electroscholar")
    Files.createDirectories(dataDirectory)
    val databasePath = dataDirectory.resolve(DATABASE_NAME)
    Files.write(databasePath, packagedDatabaseBytes())

    val properties = Properties().apply {
        setProperty("foreign_keys", "true")
    }
    val driver: SqlDriver = JdbcSqliteDriver(
        url = "jdbc:sqlite:${databasePath.toAbsolutePath()}",
        properties = properties,
    )
    return QuestionBankDatabase(driver)
}
