package io.github.ilachev.electroscholar.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.github.ilachev.electroscholar.data.Answer
import io.github.ilachev.electroscholar.data.QuestionDetail
import io.github.ilachev.electroscholar.data.QuestionRepository
import io.github.ilachev.electroscholar.data.QuestionSummary
import io.github.ilachev.electroscholar.data.Source
import io.github.ilachev.electroscholar.data.Topic
import io.github.ilachev.electroscholar.data.createDatabase

private val Ink = Color(0xFF202522)
private val Muted = Color(0xFF68716C)
private val Canvas = Color(0xFFF2F4F1)
private val Panel = Color(0xFFFAFBF9)
private val Line = Color(0xFFD8DDD9)
private val Accent = Color(0xFF176B5B)
private val AccentSoft = Color(0xFFDDEDE8)
private val Warning = Color(0xFF9A4B0D)
private val WarningSoft = Color(0xFFFFE9D5)

private val AppColors = lightColorScheme(
    primary = Accent,
    onPrimary = Color.White,
    surface = Panel,
    onSurface = Ink,
    background = Canvas,
    onBackground = Ink,
    outline = Line,
)

@Composable
fun App() {
    val repository = remember { QuestionRepository(createDatabase()) }
    val sources = remember { repository.sources() }
    var sourceId by remember { mutableStateOf(sources.firstOrNull()?.id) }
    var topicId by remember(sourceId) {
        mutableStateOf(sourceId?.let(repository::topics)?.firstOrNull()?.id)
    }
    var query by remember { mutableStateOf("") }
    var selectedQuestionId by remember(sourceId, topicId, query) {
        mutableStateOf(
            topicId?.let { repository.questions(it, query).firstOrNull()?.id }
        )
    }

    MaterialTheme(colorScheme = AppColors) {
        Surface(modifier = Modifier.fillMaxSize(), color = Canvas) {
            Column {
                AppHeader()
                HorizontalDivider(color = Line)
                Row(modifier = Modifier.fillMaxSize()) {
                    SourceAndTopicPane(
                        sources = sources,
                        selectedSourceId = sourceId,
                        selectedTopicId = topicId,
                        topics = sourceId?.let(repository::topics).orEmpty(),
                        onSourceSelected = {
                            sourceId = it
                            topicId = repository.topics(it).firstOrNull()?.id
                            query = ""
                        },
                        onTopicSelected = {
                            topicId = it
                            query = ""
                        },
                    )
                    val questions = topicId?.let { repository.questions(it, query) }.orEmpty()
                    QuestionListPane(
                        questions = questions,
                        query = query,
                        selectedQuestionId = selectedQuestionId,
                        onQueryChanged = { query = it },
                        onQuestionSelected = { selectedQuestionId = it },
                    )
                    QuestionDetailPane(
                        question = selectedQuestionId?.let(repository::question),
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun AppHeader() {
    Row(
        modifier = Modifier.fillMaxWidth().height(68.dp).background(Panel).padding(horizontal = 24.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(36.dp).clip(RoundedCornerShape(6.dp)).background(Accent),
            contentAlignment = Alignment.Center,
        ) {
            Text("E", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 19.sp)
        }
        Spacer(Modifier.width(12.dp))
        Column {
            Text("ElectroScholar", fontSize = 20.sp, fontWeight = FontWeight.SemiBold, color = Ink)
            Text("Учебная электротехника", fontSize = 12.sp, color = Muted)
        }
        Spacer(Modifier.weight(1f))
        Text("582 вопроса", fontSize = 13.sp, color = Muted)
    }
}

@Composable
private fun SourceAndTopicPane(
    sources: List<Source>,
    topics: List<Topic>,
    selectedSourceId: Long?,
    selectedTopicId: Long?,
    onSourceSelected: (Long) -> Unit,
    onTopicSelected: (Long) -> Unit,
) {
    Column(
        modifier = Modifier.width(286.dp).fillMaxHeight().background(Panel)
            .border(BorderStroke(0.5.dp, Line)).padding(18.dp),
    ) {
        SectionLabel("Дисциплина")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            sources.forEach { source ->
                val selected = source.id == selectedSourceId
                Surface(
                    modifier = Modifier.weight(1f).height(38.dp).clickable { onSourceSelected(source.id) },
                    color = if (selected) Accent else Color.Transparent,
                    contentColor = if (selected) Color.White else Ink,
                    shape = RoundedCornerShape(6.dp),
                    border = if (selected) null else BorderStroke(1.dp, Line),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(source.displayName, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                    }
                }
            }
        }
        Spacer(Modifier.height(24.dp))
        SectionLabel("Темы")
        LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            items(topics, key = { it.id }) { topic ->
                TopicRow(
                    topic = topic,
                    selected = topic.id == selectedTopicId,
                    onClick = { onTopicSelected(topic.id) },
                )
            }
        }
    }
}

@Composable
private fun TopicRow(topic: Topic, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(5.dp))
            .background(if (selected) AccentSoft else Color.Transparent)
            .clickable(onClick = onClick).padding(horizontal = 11.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            topic.name,
            modifier = Modifier.weight(1f),
            fontSize = 13.sp,
            lineHeight = 17.sp,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
            color = if (selected) Accent else Ink,
        )
        Text(topic.questionCount.toString(), fontSize = 12.sp, color = Muted)
    }
}

@Composable
private fun QuestionListPane(
    questions: List<QuestionSummary>,
    query: String,
    selectedQuestionId: Long?,
    onQueryChanged: (String) -> Unit,
    onQuestionSelected: (Long) -> Unit,
) {
    Column(
        modifier = Modifier.width(390.dp).fillMaxHeight().background(Color.White)
            .border(BorderStroke(0.5.dp, Line)),
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Вопросы", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.weight(1f))
                Text(questions.size.toString(), fontSize = 12.sp, color = Muted)
            }
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = query,
                onValueChange = onQueryChanged,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                placeholder = { Text("Номер или текст", fontSize = 13.sp) },
                singleLine = true,
                shape = RoundedCornerShape(6.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Accent,
                    unfocusedBorderColor = Line,
                ),
            )
        }
        HorizontalDivider(color = Line)
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(questions, key = { it.id }) { question ->
                QuestionRow(
                    question = question,
                    selected = question.id == selectedQuestionId,
                    onClick = { onQuestionSelected(question.id) },
                )
                HorizontalDivider(color = Line.copy(alpha = 0.65f))
            }
        }
    }
}

@Composable
private fun QuestionRow(question: QuestionSummary, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().height(82.dp)
            .background(if (selected) AccentSoft else Color.White)
            .clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 12.dp),
    ) {
        Text(
            question.number.toString().padStart(3, '0'),
            modifier = Modifier.width(40.dp),
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            color = if (selected) Accent else Muted,
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                question.text,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                fontSize = 13.sp,
                lineHeight = 18.sp,
                color = Ink,
            )
            if (question.warnings.isNotEmpty()) {
                Spacer(Modifier.height(3.dp))
                Text("Требует проверки", fontSize = 11.sp, color = Warning)
            }
        }
    }
}

@Composable
private fun QuestionDetailPane(question: QuestionDetail?, modifier: Modifier = Modifier) {
    if (question == null) {
        Box(modifier.fillMaxHeight().background(Canvas), contentAlignment = Alignment.Center) {
            Text("Нет вопросов по выбранному фильтру", color = Muted)
        }
        return
    }

    Column(
        modifier = modifier.fillMaxHeight().verticalScroll(rememberScrollState())
            .padding(horizontal = 32.dp, vertical = 24.dp),
    ) {
        Text(
            "${question.sourceFile.substringBeforeLast('.')}  /  ${question.topicName}",
            color = Muted,
            fontSize = 12.sp,
        )
        Spacer(Modifier.height(8.dp))
        Text("Вопрос ${question.number}", fontSize = 24.sp, fontWeight = FontWeight.SemiBold)
        if (question.warnings.isNotEmpty()) {
            Spacer(Modifier.height(14.dp))
            WarningBanner(question.warnings)
        }
        Spacer(Modifier.height(20.dp))
        Text(question.text, fontSize = 16.sp, lineHeight = 24.sp, color = Ink)
        question.imageFile?.let { path ->
            Spacer(Modifier.height(22.dp))
            QuestionImage(
                resourcePath = path,
                modifier = Modifier.fillMaxWidth().height(360.dp).background(Color.White)
                    .border(1.dp, Line, RoundedCornerShape(6.dp)).padding(12.dp),
            )
        }
        Spacer(Modifier.height(26.dp))
        SectionLabel("Варианты ответа")
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            question.answers.forEach { AnswerRow(it) }
        }
        if (question.hint1.isNotBlank() || question.hint2.isNotBlank()) {
            Spacer(Modifier.height(28.dp))
            HorizontalDivider(color = Line)
            Spacer(Modifier.height(22.dp))
            SectionLabel("Подсказки")
            if (question.hint1.isNotBlank()) HintBlock("1", question.hint1)
            if (question.hint2.isNotBlank()) HintBlock("2", question.hint2)
        }
        Spacer(Modifier.height(32.dp))
    }
}

@Composable
private fun AnswerRow(answer: Answer) {
    val background = if (answer.isExpected) AccentSoft else Color.White
    val border = if (answer.isExpected) Accent.copy(alpha = 0.45f) else Line
    Row(
        modifier = Modifier.fillMaxWidth().background(background, RoundedCornerShape(6.dp))
            .border(1.dp, border, RoundedCornerShape(6.dp)).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(28.dp).background(
                if (answer.isExpected) Accent else Canvas,
                CircleShape,
            ),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                answer.position.toString(),
                color = if (answer.isExpected) Color.White else Ink,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }
        Spacer(Modifier.width(12.dp))
        Text(
            answer.text.ifBlank { "Вариант показан на изображении" },
            modifier = Modifier.weight(1f),
            fontSize = 14.sp,
            color = if (answer.text.isBlank()) Muted else Ink,
        )
        if (answer.isExpected) {
            Text("Ответ по ключу", color = Accent, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun WarningBanner(warnings: String) {
    val label = when {
        "missing_correct_answer" in warnings -> "В исходной базе не задан правильный ответ"
        "invalid_answer_marker" in warnings -> "В исходной базе повреждён маркер варианта"
        else -> "Запись требует проверки"
    }
    Text(
        label,
        modifier = Modifier.fillMaxWidth().background(WarningSoft, RoundedCornerShape(6.dp))
            .padding(horizontal = 14.dp, vertical = 11.dp),
        color = Warning,
        fontSize = 13.sp,
    )
}

@Composable
private fun HintBlock(number: String, text: String) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 7.dp)) {
        Text(number, modifier = Modifier.width(28.dp), color = Accent, fontWeight = FontWeight.Bold)
        Text(text, modifier = Modifier.weight(1f), fontSize = 14.sp, lineHeight = 21.sp, color = Ink)
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text.uppercase(),
        modifier = Modifier.padding(bottom = 10.dp),
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        color = Muted,
    )
}
