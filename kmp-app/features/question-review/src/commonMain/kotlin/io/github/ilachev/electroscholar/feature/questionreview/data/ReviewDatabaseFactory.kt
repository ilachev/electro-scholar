package io.github.ilachev.electroscholar.feature.questionreview.data

internal const val REVIEW_DATABASE_NAME = "question-review.sqlite"

internal expect suspend fun createReviewDatabase(): QuestionReviewDatabase
