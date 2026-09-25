package ru.toe.data

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.Properties

actual fun createDatabase(): ToeDatabase {
    val dataDirectory = java.nio.file.Path.of(System.getProperty("user.home"), ".toe-reborn")
    Files.createDirectories(dataDirectory)
    val databasePath = dataDirectory.resolve("toe.sqlite")

    val source = checkNotNull(
        Thread.currentThread().contextClassLoader.getResourceAsStream("database/toe.sqlite")
    ) { "В ресурсах приложения отсутствует database/toe.sqlite" }
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
    return ToeDatabase(driver)
}
