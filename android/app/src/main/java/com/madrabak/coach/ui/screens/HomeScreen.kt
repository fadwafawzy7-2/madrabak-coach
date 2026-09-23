package com.madrabak.coach.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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
import com.madrabak.coach.data.api.Dashboard
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.data.repo.safeCall
import com.madrabak.coach.util.MacroMath
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(
    onNavigateToFood: () -> Unit,
    onNavigateToCoach: () -> Unit,
    onNavigateToProgress: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var dashboard by remember { mutableStateOf<Dashboard?>(null) }
    var coachTip by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(true) }
    var offline by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        val api = ApiProvider.init(context)
        safeCall { api.dashboard() }
            .onSuccess { dashboard = it; offline = false }
            .onFailure { offline = true }
        loading = false
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.your_day), style = MaterialTheme.typography.headlineMedium)

        if (loading) {
            CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
        } else if (offline) {
            Text(stringResource(R.string.error_no_internet), color = MaterialTheme.colorScheme.error)
        }

        dashboard?.let { d ->
            // Calories card — big readable numbers
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
                Column(Modifier.fillMaxWidth().padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    val remaining = d.remaining?.kcal?.toInt() ?: 0
                    Text("$remaining", style = MaterialTheme.typography.displayLarge,
                        color = MaterialTheme.colorScheme.onPrimaryContainer)
                    Text("${stringResource(R.string.calories_remaining)} (${stringResource(R.string.kcal_unit)})",
                        style = MaterialTheme.typography.bodyLarge)
                    Spacer(Modifier.height(12.dp))
                    val target = d.target?.kcal ?: 0
                    val consumed = d.consumed.kcal.toInt()
                    LinearProgressIndicator(
                        progress = { MacroMath.progress(consumed.toDouble(), target.toDouble()) },
                        modifier = Modifier.fillMaxWidth().height(10.dp),
                    )
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("${stringResource(R.string.calories_consumed)}: $consumed")
                        Text("${stringResource(R.string.calories_target)}: $target")
                    }
                }
            }

            // Macros row
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                MacroCard(stringResource(R.string.protein), d.consumed.proteinG, d.target?.proteinG, Modifier.weight(1f))
                MacroCard(stringResource(R.string.carbs), d.consumed.carbsG, d.target?.carbsG, Modifier.weight(1f))
                MacroCard(stringResource(R.string.fat), d.consumed.fatG, d.target?.fatG, Modifier.weight(1f))
            }

            // Morning weight
            Card {
                Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(stringResource(R.string.morning_weight))
                    Text(
                        d.morningWeightKg?.let { "$it kg" } ?: stringResource(R.string.no_morning_weight),
                        style = MaterialTheme.typography.labelLarge,
                    )
                }
            }
        }

        // «مدربك يقول…»
        Card {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text(stringResource(R.string.coach_says), style = MaterialTheme.typography.titleLarge)
                Spacer(Modifier.height(8.dp))
                if (coachTip != null) {
                    Text(coachTip!!)
                } else {
                    OutlinedButton(onClick = {
                        scope.launch {
                            val api = ApiProvider.init(context)
                            safeCall { api.whatToEat() }
                                .onSuccess { coachTip = it.suggestion }
                                .onFailure { coachTip = context.getString(R.string.error_ai_unavailable) }
                        }
                    }) { Text(stringResource(R.string.action_what_to_eat)) }
                }
            }
        }

        // Primary actions
        Button(onClick = onNavigateToFood, modifier = Modifier.fillMaxWidth().height(52.dp)) {
            Text(stringResource(R.string.action_photo_meal))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedButton(onClick = onNavigateToCoach, modifier = Modifier.weight(1f)) {
                Text(stringResource(R.string.action_ask_coach))
            }
            OutlinedButton(onClick = onNavigateToProgress, modifier = Modifier.weight(1f)) {
                Text(stringResource(R.string.action_log_weight))
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun MacroCard(label: String, consumed: Double, target: Int?, modifier: Modifier = Modifier) {
    Card(modifier) {
        Column(Modifier.padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(label, style = MaterialTheme.typography.bodyMedium)
            Text("${consumed.toInt()}", style = MaterialTheme.typography.titleLarge)
            Text("/ ${target ?: "—"}", style = MaterialTheme.typography.bodyMedium)
            LinearProgressIndicator(
                progress = { MacroMath.progress(consumed, (target ?: 0).toDouble()) },
                modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
            )
        }
    }
}
