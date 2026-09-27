package io.github.ilachev.electroscholar.data

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.Properties

actual fun createDatabase(): QuestionBankDatabase {
    val dataDirectory = java.nio.file.Path.of(System.getProperty("user.home"), ".electroscholar")
    Files.createDirectories(dataDirectory)
    val databasePath = dataDirectory.resolve("question-bank.sqlite")

    val source = checkNotNull(
        Thread.currentThread().contextClassLoader.getResourceAsStream("database/question-bank.sqlite")
    ) { "В ресурсах приложения отсутствует database/question-bank.sqlite" }
    source.use {
        Files.copy(it, databasePath, StandardCopyOption.REPLACE_EXISTING)
    }

    val properties = Properties().apply {
        setProperty("foreign_keys", "true")
    }
    val driver: SqlDriver = JdbcSqliteDriver(
        url = "jdbc:sqlite:${databasePath.toAbsolutePath()}",
        properties = properties,
    )
    return QuestionBankDatabase(driver)
}
