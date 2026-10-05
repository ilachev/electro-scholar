package io.github.ilachev.electroscholar.feature.questionreview

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.github.ilachev.electroscholar.feature.questionreview.data.ReviewRepository
import io.github.ilachev.electroscholar.feature.questionreview.data.createReviewDatabase
import kotlinx.coroutines.launch

private val Ink = Color(0xFF202522)
private val Muted = Color(0xFF68716C)
private val Canvas = Color(0xFFF2F4F1)
private val Panel = Color(0xFFFFFFFF)
private val Line = Color(0xFFD8DDD9)
private val Accent = Color(0xFF176B5B)
private val AccentSoft = Color(0xFFDDEDE8)
private val Warning = Color(0xFF9A4B0D)
private val WarningSoft = Color(0xFFFFE9D5)
private val Reject = Color(0xFF9E2A2B)

private val ReviewColors = lightColorScheme(
    primary = Accent,
    onPrimary = Color.White,
    surface = Panel,
    onSurface = Ink,
    background = Canvas,
    onBackground = Ink,
    outline = Line,
    error = Reject,
)

private sealed interface ReviewLoadState {
    data object Loading : ReviewLoadState
    data class Ready(
        val inputs: List<QuestionReviewInput>,
        val documents: List<ReviewDocument>,
        val repository: ReviewRepository,
    ) : ReviewLoadState
    data class Failed(val message: String) : ReviewLoadState
}

@Composable
fun QuestionReviewFeature(
    inputProvider: suspend () -> List<QuestionReviewInput>,
    onBack: () -> Unit,
    sourceImage: @Composable (
        input: QuestionReviewInput,
        crop: SourceBounds?,
        modifier: Modifier,
    ) -> Unit,
) {
    val state by produceState<ReviewLoadState>(ReviewLoadState.Loading) {
        value = try {
            val inputs = inputProvider()
            val documents = inputs.map(::parseQuestionIr)
            val repository = ReviewRepository(createReviewDatabase())
            documents.zip(inputs).forEach { (document, input) ->
                repository.registerDocument(
                    documentId = document.documentId,
                    schemaVersion = document.schemaVersion,
                    documentJson = input.documentJson,
                )
            }
            ReviewLoadState.Ready(
                inputs = inputs,
                documents = documents,
                repository = repository,
            )
        } catch (error: Throwable) {
            ReviewLoadState.Failed(error.message ?: "Не удалось открыть очередь ревью")
        }
    }

    MaterialTheme(colorScheme = ReviewColors) {
        Surface(
            modifier = Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing),
            color = Canvas,
        ) {
            when (val current = state) {
                ReviewLoadState.Loading -> LoadingPane()
                is ReviewLoadState.Failed -> FailurePane(current.message, onBack)
                is ReviewLoadState.Ready -> ReviewWorkspace(
                    documents = current.documents,
                    inputs = current.inputs,
                    repository = current.repository,
                    onBack = onBack,
                    sourceImage = sourceImage,
                )
            }
        }
    }
}

@Composable
private fun LoadingPane() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(strokeWidth = 3.dp)
            Spacer(Modifier.height(14.dp))
            Text("Открываем очередь ревью", color = Muted, fontSize = 14.sp)
        }
    }
}

@Composable
private fun FailurePane(message: String, onBack: () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        ReviewHeader("Ошибка ревью", message, onBack, null)
        Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
            Text(message, color = Reject)
        }
    }
}

@Composable
private fun ReviewWorkspace(
    documents: List<ReviewDocument>,
    inputs: List<QuestionReviewInput>,
    repository: ReviewRepository,
    onBack: () -> Unit,
    sourceImage: @Composable (QuestionReviewInput, SourceBounds?, Modifier) -> Unit,
) {
    if (documents.isEmpty()) {
        FailurePane("В runtime-базе пока нет документов Question IR", onBack)
        return
    }

    var selectedDocumentId by remember(documents) { mutableStateOf(documents.first().documentId) }
    val document = documents.first { it.documentId == selectedDocumentId }
    val input = inputs[documents.indexOf(document)]
    var selectedNodeId by remember(selectedDocumentId) { mutableStateOf(document.nodes.first().id) }
    val node = document.nodes.firstOrNull { it.id == selectedNodeId } ?: document.nodes.first()
    var reviewState by remember(selectedDocumentId) {
        mutableStateOf(repository.state(selectedDocumentId))
    }
    val reviewedCount = reviewState.nodes.values.count {
        it.latestDecision == ReviewDecision.Accept || it.latestDecision == ReviewDecision.Correct
    }

    Column(Modifier.fillMaxSize()) {
        ReviewHeader(
            title = "Проверка Question IR",
            subtitle = "${document.sourceFile} / вопрос ${document.questionNumber}",
            onBack = onBack,
            progress = "$reviewedCount из ${document.nodes.size}",
        )
        HorizontalDivider(color = Line)
        BoxWithConstraints(Modifier.fillMaxSize()) {
            if (maxWidth >= 1120.dp) {
                Row(Modifier.fillMaxSize()) {
                    DocumentQueue(
                        documents = documents,
                        selectedDocumentId = selectedDocumentId,
                        states = documents.associate { it.documentId to repository.state(it.documentId) },
                        onSelected = {
                            selectedDocumentId = it
                            selectedNodeId = documents.first { document ->
                                document.documentId == it
                            }.nodes.first().id
                            reviewState = repository.state(it)
                        },
                        modifier = Modifier.width(244.dp),
                    )
                    EvidencePane(
                        document = document,
                        input = input,
                        node = node,
                        nodes = document.nodes,
                        reviewState = reviewState,
                        onNodeSelected = { selectedNodeId = it },
                        sourceImage = sourceImage,
                        modifier = Modifier.width(454.dp),
                    )
                    ReviewEditor(
                        document = document,
                        node = node,
                        stored = reviewState.nodes[node.id],
                        repository = repository,
                        onSaved = { reviewState = repository.state(document.documentId) },
                        modifier = Modifier.weight(1f),
                    )
                }
            } else {
                Column(
                    Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    CompactDocumentSelector(documents, selectedDocumentId) {
                        selectedDocumentId = it
                        selectedNodeId = documents.first { document ->
                            document.documentId == it
                        }.nodes.first().id
                        reviewState = repository.state(it)
                    }
                    EvidencePreview(document, input, node, sourceImage)
                    NodeList(
                        nodes = document.nodes,
                        selectedNodeId = node.id,
                        reviewState = reviewState,
                        onSelected = { selectedNodeId = it },
                    )
                    ReviewEditor(
                        document = document,
                        node = node,
                        stored = reviewState.nodes[node.id],
                        repository = repository,
                        onSaved = { reviewState = repository.state(document.documentId) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

@Composable
private fun ReviewHeader(
    title: String,
    subtitle: String,
    onBack: () -> Unit,
    progress: String?,
) {
    Row(
        modifier = Modifier.fillMaxWidth().height(68.dp).background(Panel).padding(horizontal = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
        }
        Spacer(Modifier.width(4.dp))
        Column(Modifier.weight(1f)) {
            Text(title, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
            Text(
                subtitle,
                color = Muted,
                fontSize = 12.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        progress?.let {
            Text(it, color = Accent, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
        }
    }
}

@Composable
private fun DocumentQueue(
    documents: List<ReviewDocument>,
    selectedDocumentId: String,
    states: Map<String, DocumentReviewState>,
    onSelected: (String) -> Unit,
    modifier: Modifier,
) {
    Column(modifier.fillMaxHeight().background(Panel).border(0.5.dp, Line)) {
        Column(Modifier.padding(16.dp)) {
            SectionLabel("Очередь")
            Text("Документы Question IR", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
        }
        HorizontalDivider(color = Line)
        LazyColumn(Modifier.fillMaxSize()) {
            items(documents, key = { it.documentId }) { document ->
                val reviewed = states[document.documentId]?.nodes?.values?.count {
                    it.latestDecision == ReviewDecision.Accept ||
                        it.latestDecision == ReviewDecision.Correct
                } ?: 0
                val selected = document.documentId == selectedDocumentId
                Column(
                    Modifier.fillMaxWidth().background(if (selected) AccentSoft else Panel)
                        .clickable { onSelected(document.documentId) }
                        .padding(horizontal = 16.dp, vertical = 14.dp),
                ) {
                    Text(
                        "Вопрос ${document.questionNumber}",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = if (selected) Accent else Ink,
                    )
                    Spacer(Modifier.height(3.dp))
                    Text(document.documentId, fontSize = 11.sp, color = Muted)
                    Spacer(Modifier.height(6.dp))
                    Text("$reviewed / ${document.nodes.size}", fontSize = 11.sp, color = Muted)
                }
                HorizontalDivider(color = Line)
            }
        }
    }
}

@Composable
private fun CompactDocumentSelector(
    documents: List<ReviewDocument>,
    selectedDocumentId: String,
    onSelected: (String) -> Unit,
) {
    if (documents.size == 1) return
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        documents.forEach { document ->
            OutlinedButton(
                onClick = { onSelected(document.documentId) },
                border = BorderStroke(
                    1.dp,
                    if (document.documentId == selectedDocumentId) Accent else Line,
                ),
            ) {
                Text("${document.sourceFile} / ${document.questionNumber}")
            }
        }
    }
}

@Composable
private fun EvidencePane(
    document: ReviewDocument,
    input: QuestionReviewInput,
    node: ReviewNode,
    nodes: List<ReviewNode>,
    reviewState: DocumentReviewState,
    onNodeSelected: (String) -> Unit,
    sourceImage: @Composable (QuestionReviewInput, SourceBounds?, Modifier) -> Unit,
    modifier: Modifier,
) {
    Column(modifier.fillMaxHeight().background(Canvas).border(0.5.dp, Line)) {
        Column(Modifier.padding(18.dp)) {
            EvidencePreview(document, input, node, sourceImage)
        }
        HorizontalDivider(color = Line)
        LazyColumn(Modifier.fillMaxSize().background(Panel)) {
            items(nodes, key = { it.id }) { item ->
                NodeRow(
                    node = item,
                    selected = item.id == node.id,
                    stored = reviewState.nodes[item.id],
                    onClick = { onNodeSelected(item.id) },
                )
                HorizontalDivider(color = Line.copy(alpha = 0.7f))
            }
        }
    }
}

@Composable
private fun EvidencePreview(
    document: ReviewDocument,
    input: QuestionReviewInput,
    node: ReviewNode,
    sourceImage: @Composable (QuestionReviewInput, SourceBounds?, Modifier) -> Unit,
) {
    SectionLabel("Оригинал")
    sourceImage(
        input,
        null,
        Modifier.fillMaxWidth().aspectRatio(document.imageWidth.toFloat() / document.imageHeight)
            .background(Color.White).border(1.dp, Line, RoundedCornerShape(6.dp)).padding(8.dp),
    )
    Spacer(Modifier.height(14.dp))
    SectionLabel("Выбранная область")
    if (node.bounds != null) {
        sourceImage(
            input,
            node.bounds,
            Modifier.fillMaxWidth().heightIn(min = 92.dp, max = 210.dp)
                .aspectRatio(node.bounds.width.toFloat() / node.bounds.height)
                .background(Color.White).border(1.dp, Line, RoundedCornerShape(6.dp)),
        )
        Spacer(Modifier.height(7.dp))
        Text(
            "x=${node.bounds.x}, y=${node.bounds.y}, ${node.bounds.width} × ${node.bounds.height}",
            color = Muted,
            fontSize = 11.sp,
        )
    } else {
        Box(
            Modifier.fillMaxWidth().height(72.dp).background(Panel)
                .border(1.dp, Line, RoundedCornerShape(6.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Text("Для фрагмента не задана область", color = Muted, fontSize = 12.sp)
        }
    }
    Spacer(Modifier.height(16.dp))
    Text("Фрагменты", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun NodeList(
    nodes: List<ReviewNode>,
    selectedNodeId: String,
    reviewState: DocumentReviewState,
    onSelected: (String) -> Unit,
) {
    Column(Modifier.fillMaxWidth().background(Panel).border(1.dp, Line)) {
        nodes.forEach { node ->
            NodeRow(
                node = node,
                selected = node.id == selectedNodeId,
                stored = reviewState.nodes[node.id],
                onClick = { onSelected(node.id) },
            )
            HorizontalDivider(color = Line)
        }
    }
}

@Composable
private fun NodeRow(
    node: ReviewNode,
    selected: Boolean,
    stored: StoredNodeReview?,
    onClick: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().background(if (selected) AccentSoft else Panel)
            .clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        DecisionMark(stored?.latestDecision)
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(
                node.label,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                fontSize = 13.sp,
                fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
            )
            Text(
                "${node.section} · ${kindLabel(node.kind)}",
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                fontSize = 10.sp,
                color = Muted,
            )
        }
    }
}

@Composable
private fun DecisionMark(decision: ReviewDecision?) {
    val color = when (decision) {
        ReviewDecision.Accept, ReviewDecision.Correct -> Accent
        ReviewDecision.Reject -> Reject
        ReviewDecision.Defer -> Warning
        null -> Line
    }
    Box(Modifier.size(9.dp).background(color, RoundedCornerShape(2.dp)))
}

@Composable
private fun ReviewEditor(
    document: ReviewDocument,
    node: ReviewNode,
    stored: StoredNodeReview?,
    repository: ReviewRepository,
    onSaved: () -> Unit,
    modifier: Modifier,
) {
    var draft by remember(document.documentId, node.id, stored?.draftValue) {
        mutableStateOf(stored?.draftValue ?: node.originalValue)
    }
    var draftPlainText by remember(document.documentId, node.id, stored?.draftPlainText) {
        mutableStateOf(stored?.draftPlainText ?: node.originalPlainText)
    }
    var reviewer by remember { mutableStateOf("") }
    var comment by remember(document.documentId, node.id, stored?.comment) {
        mutableStateOf(stored?.comment.orEmpty())
    }
    var message by remember(document.documentId, node.id) { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val issues = candidateIssues(node, draft) + if (
        node.kind == ReviewNodeKind.Formula && draftPlainText.isNullOrBlank()
    ) {
        listOf("Печатное представление формулы не заполнено")
    } else {
        emptyList()
    }
    val hasChanges = draft != node.originalValue || draftPlainText != node.originalPlainText
    val canSubmit = reviewer.isNotBlank() && issues.isEmpty()

    fun submit(decision: ReviewDecision) {
        scope.launch {
            try {
                repository.record(
                    documentId = document.documentId,
                    node = node,
                    draftValue = draft,
                    draftPlainText = draftPlainText,
                    reviewer = reviewer,
                    decision = decision,
                    comment = comment,
                )
                onSaved()
                message = "Решение сохранено в локальном журнале"
            } catch (error: Throwable) {
                message = error.message ?: "Не удалось сохранить решение"
            }
        }
    }

    Column(
        modifier.fillMaxHeight().background(Panel).padding(20.dp)
            .verticalScroll(rememberScrollState()),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(node.label, fontSize = 19.sp, fontWeight = FontWeight.SemiBold)
                Text(node.id, color = Muted, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }
            StatusBadge(stored?.latestDecision)
        }
        Spacer(Modifier.height(20.dp))
        MetadataLine("Тип", kindLabel(node.kind))
        MetadataLine("Статус источника", node.sourceReviewStatus)
        Spacer(Modifier.height(18.dp))

        if (node.kind == ReviewNodeKind.Formula) {
            SectionLabel("Печатное представление")
            OutlinedTextField(
                value = draftPlainText.orEmpty(),
                onValueChange = {
                    draftPlainText = it
                    message = null
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Текст для поиска и доступности") },
                supportingText = {
                    if (draftPlainText != node.originalPlainText) {
                        Text("Есть локальная правка; исходный JSON не изменён")
                    }
                },
            )
            Spacer(Modifier.height(18.dp))
        }

        SectionLabel(if (node.editable) "Редактор" else "Ссылка на данные")
        OutlinedTextField(
            value = draft,
            onValueChange = {
                if (node.editable) {
                    draft = it
                    message = null
                }
            },
            modifier = Modifier.fillMaxWidth().heightIn(min = 118.dp),
            readOnly = !node.editable,
            textStyle = androidx.compose.ui.text.TextStyle(
                fontFamily = if (node.kind == ReviewNodeKind.Formula) {
                    FontFamily.Monospace
                } else {
                    FontFamily.Default
                },
                fontSize = 14.sp,
            ),
            supportingText = {
                if (hasChanges) {
                    Text("Есть локальная правка; исходный JSON не изменён")
                }
            },
        )

        Spacer(Modifier.height(18.dp))
        SectionLabel("Автоматические проверки")
        if (issues.isEmpty()) {
            CheckLine("Поле заполнено и базовые ограничения соблюдены", passed = true)
            if (node.kind == ReviewNodeKind.Formula) {
                CheckLine("Скобки сбалансированы, опасные команды не найдены", passed = true)
                CheckLine("Изолированная компиляция и visual diff ещё не подключены", passed = false)
            }
        } else {
            issues.forEach { CheckLine(it, passed = false) }
        }
        document.checks.forEach { check ->
            CheckLine(
                "${checkLabel(check.kind)}: ${check.method ?: check.status}",
                passed = check.status == "passed",
            )
        }

        Spacer(Modifier.height(20.dp))
        OutlinedTextField(
            value = reviewer,
            onValueChange = { reviewer = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Проверяющий") },
            placeholder = { Text("Имя или устойчивый идентификатор") },
            singleLine = true,
        )
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(
            value = comment,
            onValueChange = { comment = it },
            modifier = Modifier.fillMaxWidth().heightIn(min = 88.dp),
            label = { Text("Комментарий") },
        )
        Spacer(Modifier.height(16.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = { submit(ReviewDecision.Accept) },
                enabled = canSubmit && !hasChanges,
            ) {
                Icon(Icons.Default.Check, contentDescription = null, Modifier.size(17.dp))
                Spacer(Modifier.width(7.dp))
                Text("Принять")
            }
            OutlinedButton(
                onClick = { submit(ReviewDecision.Correct) },
                enabled = canSubmit && node.editable && hasChanges,
            ) {
                Icon(Icons.Default.Edit, contentDescription = null, Modifier.size(17.dp))
                Spacer(Modifier.width(7.dp))
                Text("Исправить и принять")
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(
                onClick = { submit(ReviewDecision.Defer) },
                enabled = reviewer.isNotBlank(),
            ) {
                Text("Отложить")
            }
            TextButton(
                onClick = { submit(ReviewDecision.Reject) },
                enabled = reviewer.isNotBlank(),
                colors = ButtonDefaults.textButtonColors(contentColor = Reject),
            ) {
                Icon(Icons.Default.Close, contentDescription = null, Modifier.size(17.dp))
                Spacer(Modifier.width(7.dp))
                Text("Отклонить")
            }
        }
        message?.let {
            Spacer(Modifier.height(12.dp))
            Text(it, color = if (it.startsWith("Решение")) Accent else Reject, fontSize = 12.sp)
        }
        stored?.submittedAt?.let {
            Spacer(Modifier.height(14.dp))
            Text("Последнее решение: $it", color = Muted, fontSize = 11.sp)
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun StatusBadge(decision: ReviewDecision?) {
    val (label, background, foreground) = when (decision) {
        ReviewDecision.Accept -> Triple("Принято", AccentSoft, Accent)
        ReviewDecision.Correct -> Triple("Исправлено", AccentSoft, Accent)
        ReviewDecision.Reject -> Triple("Отклонено", Color(0xFFF8DEDE), Reject)
        ReviewDecision.Defer -> Triple("Отложено", WarningSoft, Warning)
        null -> Triple("Не проверено", Canvas, Muted)
    }
    Text(
        label,
        modifier = Modifier.background(background, RoundedCornerShape(5.dp))
            .padding(horizontal = 9.dp, vertical = 5.dp),
        color = foreground,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
    )
}

@Composable
private fun CheckLine(text: String, passed: Boolean) {
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.Top) {
        Text(if (passed) "✓" else "!", color = if (passed) Accent else Warning, fontWeight = FontWeight.Bold)
        Spacer(Modifier.width(9.dp))
        Text(text, modifier = Modifier.weight(1f), fontSize = 12.sp, color = Ink, lineHeight = 17.sp)
    }
}

@Composable
private fun MetadataLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Text(label, modifier = Modifier.width(132.dp), color = Muted, fontSize = 12.sp)
        Text(value, modifier = Modifier.weight(1f), color = Ink, fontSize = 12.sp)
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text.uppercase(),
        modifier = Modifier.padding(bottom = 8.dp),
        fontSize = 10.sp,
        fontWeight = FontWeight.SemiBold,
        color = Muted,
    )
}

private fun kindLabel(kind: ReviewNodeKind): String = when (kind) {
    ReviewNodeKind.Text -> "текст"
    ReviewNodeKind.Formula -> "LaTeX"
    ReviewNodeKind.Circuit -> "схема"
    ReviewNodeKind.AnswerKey -> "ключ"
}

private fun checkLabel(kind: String): String = when (kind) {
    "source_match" -> "Исходное изображение"
    "text_transcription" -> "Текст"
    "formula_render" -> "Формулы"
    "circuit_topology" -> "Топология схемы"
    "answer_key" -> "Ключ ответа"
    else -> kind
}
