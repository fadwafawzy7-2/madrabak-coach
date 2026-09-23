package com.madrabak.coach.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.madrabak.coach.R
import com.madrabak.coach.data.api.ChatIn
import com.madrabak.coach.data.api.ChatMessage
import com.madrabak.coach.data.repo.ApiError
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.data.repo.safeCall
import kotlinx.coroutines.launch

@Composable
fun CoachScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val messages = remember { mutableStateListOf<ChatMessage>() }
    var input by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()

    LaunchedEffect(Unit) {
        safeCall { ApiProvider.init(context).chatHistory() }
            .onSuccess { messages.clear(); messages.addAll(it.messages) }
    }
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    fun send(text: String) {
        if (text.isBlank() || sending) return
        messages.add(ChatMessage("user", text))
        input = ""
        sending = true
        scope.launch {
            safeCall { ApiProvider.init(context).chat(ChatIn(text)) }
                .onSuccess { messages.add(ChatMessage("assistant", it.reply)) }
                .onFailure { e ->
                    val msg = when (e) {
                        is ApiError.LimitReached -> context.getString(R.string.error_limit_reached)
                        is ApiError.NoInternet -> context.getString(R.string.error_no_internet)
                        else -> context.getString(R.string.error_ai_unavailable)
                    }
                    messages.add(ChatMessage("assistant", msg))
                }
            sending = false
        }
    }

    Column(Modifier.fillMaxSize()) {
        Text(
            stringResource(R.string.coach_title),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(16.dp),
        )
        Text(
            stringResource(R.string.coach_disclaimer),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.outline,
            modifier = Modifier.padding(horizontal = 16.dp),
        )

        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).fillMaxWidth().padding(horizontal = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(messages.toList()) { msg ->
                val isUser = msg.role == "user"
                Box(Modifier.fillMaxWidth(), contentAlignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart) {
                    Surface(
                        color = if (isUser) MaterialTheme.colorScheme.primaryContainer
                        else MaterialTheme.colorScheme.surfaceVariant,
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.widthIn(max = 300.dp),
                    ) {
                        Text(msg.content, modifier = Modifier.padding(12.dp))
                    }
                }
            }
        }

        // quick actions
        Row(Modifier.padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            AssistChip(onClick = {
                scope.launch {
                    sending = true
                    safeCall { ApiProvider.init(context).whatToEat() }
                        .onSuccess { messages.add(ChatMessage("assistant", it.suggestion)) }
                        .onFailure { messages.add(ChatMessage("assistant", context.getString(R.string.error_ai_unavailable))) }
                    sending = false
                }
            }, label = { Text(stringResource(R.string.action_what_to_eat)) })
            AssistChip(onClick = {
                scope.launch {
                    sending = true
                    safeCall { ApiProvider.init(context).saveMyDay() }
                        .onSuccess { messages.add(ChatMessage("assistant", it.suggestion)) }
                        .onFailure { messages.add(ChatMessage("assistant", context.getString(R.string.error_ai_unavailable))) }
                    sending = false
                }
            }, label = { Text(stringResource(R.string.save_my_day)) })
        }

        Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = input, onValueChange = { input = it },
                placeholder = { Text(stringResource(R.string.type_message)) },
                modifier = Modifier.weight(1f),
            )
            Spacer(Modifier.width(8.dp))
            IconButton(onClick = { send(input) }, enabled = !sending && input.isNotBlank()) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = stringResource(R.string.send))
            }
        }
    }
}
