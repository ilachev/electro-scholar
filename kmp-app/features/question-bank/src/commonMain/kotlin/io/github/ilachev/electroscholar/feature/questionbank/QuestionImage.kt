package io.github.ilachev.electroscholar.feature.questionbank

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.Layout
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Constraints
import io.github.ilachev.electroscholar.feature.questionbank.resources.Res
import io.github.ilachev.electroscholar.feature.questionbank.resources.allDrawableResources
import org.jetbrains.compose.resources.painterResource
import kotlin.math.roundToInt

data class QuestionImageCrop(
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int,
)

@Composable
internal fun QuestionImage(resourcePath: String, modifier: Modifier) {
    QuestionSourceImage(resourcePath, crop = null, modifier = modifier)
}

@Composable
fun QuestionSourceImage(
    resourcePath: String,
    crop: QuestionImageCrop?,
    modifier: Modifier,
) {
    val resourceName = resourcePath.substringAfterLast('/').substringBeforeLast('.').lowercase()
    val resource = Res.allDrawableResources[resourceName]

    if (resource == null) {
        Box(modifier = modifier, contentAlignment = Alignment.Center) {
            Text("Изображение не найдено", textAlign = TextAlign.Center)
        }
    } else {
        val painter = painterResource(resource)
        if (crop == null) {
            Image(
                painter = painter,
                contentDescription = null,
                modifier = modifier,
                contentScale = ContentScale.Fit,
            )
        } else {
            Layout(
                modifier = modifier.clipToBounds(),
                content = {
                    Image(
                        painter = painter,
                        contentDescription = null,
                        contentScale = ContentScale.FillBounds,
                    )
                },
            ) { measurables, constraints ->
                val viewportWidth = constraints.maxWidth
                val viewportHeight = constraints.maxHeight
                val scaleX = viewportWidth.toFloat() / crop.width
                val scaleY = viewportHeight.toFloat() / crop.height
                val renderedWidth = (painter.intrinsicSize.width * scaleX).roundToInt()
                val renderedHeight = (painter.intrinsicSize.height * scaleY).roundToInt()
                val image = measurables.single().measure(
                    Constraints.fixed(renderedWidth, renderedHeight),
                )
                layout(viewportWidth, viewportHeight) {
                    image.placeRelative(
                        x = -(crop.x * scaleX).roundToInt(),
                        y = -(crop.y * scaleY).roundToInt(),
                    )
                }
            }
        }
    }
}
