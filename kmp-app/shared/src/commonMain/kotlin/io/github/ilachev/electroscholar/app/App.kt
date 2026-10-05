package io.github.ilachev.electroscholar.app

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import io.github.ilachev.electroscholar.feature.questionbank.QuestionImageCrop
import io.github.ilachev.electroscholar.feature.questionbank.QuestionBankFeature
import io.github.ilachev.electroscholar.feature.questionbank.QuestionSourceImage
import io.github.ilachev.electroscholar.feature.questionbank.loadStructuredQuestionDocuments
import io.github.ilachev.electroscholar.feature.questionreview.QuestionReviewFeature
import io.github.ilachev.electroscholar.feature.questionreview.QuestionReviewInput

private enum class AppScreen {
    QuestionBank,
    QuestionReview,
}

@Composable
fun App() {
    var screen by remember { mutableStateOf(AppScreen.QuestionBank) }
    when (screen) {
        AppScreen.QuestionBank -> QuestionBankFeature(
            onOpenReview = { screen = AppScreen.QuestionReview },
        )
        AppScreen.QuestionReview -> QuestionReviewFeature(
            inputProvider = {
                loadStructuredQuestionDocuments().map { document ->
                    QuestionReviewInput(
                        questionId = document.questionId,
                        questionNumber = document.questionNumber,
                        sourceFile = document.sourceFile,
                        sourceIndex = document.sourceIndex,
                        imageFile = document.imageFile,
                        documentJson = document.documentJson,
                    )
                }
            },
            onBack = { screen = AppScreen.QuestionBank },
            sourceImage = { input, crop, modifier ->
                val imageFile = input.imageFile
                if (imageFile != null) {
                    QuestionSourceImage(
                        resourcePath = imageFile,
                        crop = crop?.let {
                            QuestionImageCrop(it.x, it.y, it.width, it.height)
                        },
                        modifier = modifier,
                    )
                }
            },
        )
    }
}
