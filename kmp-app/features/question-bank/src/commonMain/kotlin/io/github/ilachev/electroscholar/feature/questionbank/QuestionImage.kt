package io.github.ilachev.electroscholar.feature.questionbank

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import io.github.ilachev.electroscholar.feature.questionbank.resources.Res
import io.github.ilachev.electroscholar.feature.questionbank.resources.allDrawableResources
import org.jetbrains.compose.resources.painterResource

@Composable
internal fun QuestionImage(resourcePath: String, modifier: Modifier) {
    val resourceName = resourcePath.substringAfterLast('/').substringBeforeLast('.').lowercase()
    val resource = Res.allDrawableResources[resourceName]

    if (resource == null) {
        Box(modifier = modifier, contentAlignment = Alignment.Center) {
            Text("Изображение не найдено", textAlign = TextAlign.Center)
        }
    } else {
        Image(
            painter = painterResource(resource),
            contentDescription = null,
            modifier = modifier,
            contentScale = ContentScale.Fit,
        )
    }
}
