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
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import com.madrabak.coach.data.api.BodyFatIn
import com.madrabak.coach.data.api.MeasurementIn
import com.madrabak.coach.data.api.WeeklyReview
import com.madrabak.coach.data.api.WeightSummary
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.data.repo.safeCall
import kotlinx.coroutines.launch

@Composable
fun ProgressScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var weight by remember { mutableStateOf("") }
    var isMorning by remember { mutableStateOf(true) }
    var summary by remember { mutableStateOf<WeightSummary?>(null) }
    var review by remember { mutableStateOf<WeeklyReview?>(null) }
    var waist by remember { mutableStateOf("") }
    var neck by remember { mutableStateOf("") }
    var hip by remember { mutableStateOf("") }
    var bodyFat by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        scope.launch {
            safeCall { ApiProvider.init(context).weightSummary() }.onSuccess { summary = it }
        }
    }
    LaunchedEffect(Unit) { refresh() }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.nav_progress), style = MaterialTheme.typography.headlineMedium)

        // ---- weight logging
        Card {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(stringResource(R.string.log_weight_title), style = MaterialTheme.typography.titleLarge)
                Text(stringResource(R.string.morning_weight_tip), style = MaterialTheme.typography.bodyMedium)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = weight, onValueChange = { weight = it },
                        label = { Text(stringResource(R.string.weight_kg)) },
                        modifier = Modifier.weight(1f), singleLine = true,
                    )
                    Spacer(Modifier.width(8.dp))
                    Button(onClick = {
                        val v = weight.toDoubleOrNull() ?: return@Button
                        scope.launch {
                            safeCall { ApiProvider.init(context).logMeasurement(MeasurementIn("weight", v, isMorning)) }
                                .onSuccess { weight = ""; message = null; refresh() }
                                .onFailure { message = context.getString(R.string.error_invalid_input) }
                        }
                    }, enabled = weight.toDoubleOrNull() != null) { Text(stringResource(R.string.save)) }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = isMorning, onCheckedChange = { isMorning = it })
                    Text(stringResource(R.string.is_morning_weight))
                }
            }
        }
        message?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        // ---- weekly averages / trend
        summary?.let { s ->
            Card {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(stringResource(R.string.weight_trend), style = MaterialTheme.typography.titleLarge)
                    s.weekOverWeekKg?.let { t ->
                        Text("${if (t > 0) "+" else ""}$t kg", style = MaterialTheme.typography.headlineMedium,
                            color = MaterialTheme.colorScheme.primary)
                    }
                    s.weeklyAverages.takeLast(4).forEach { w ->
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(w.weekStart)
                            Text("${w.avgKg} kg (${w.count})", style = MaterialTheme.typography.labelLarge)
                        }
                    }
                }
            }
        }

        // ---- body fat estimate
        Card {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(stringResource(R.string.body_fat_estimate), style = MaterialTheme.typography.titleLarge)
                Text(stringResource(R.string.body_fat_disclaimer), style = MaterialTheme.typography.bodyMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = waist, onValueChange = { waist = it },
                        label = { Text(stringResource(R.string.waist_cm)) }, modifier = Modifier.weight(1f))
                    OutlinedTextField(value = neck, onValueChange = { neck = it },
                        label = { Text(stringResource(R.string.neck_cm)) }, modifier = Modifier.weight(1f))
                    OutlinedTextField(value = hip, onValueChange = { hip = it },
                        label = { Text(stringResource(R.string.hip_cm)) }, modifier = Modifier.weight(1f))
                }
                OutlinedButton(onClick = {
                    scope.launch {
                        safeCall {
                            ApiProvider.init(context).bodyFat(BodyFatIn(
                                waistCm = waist.toDouble(), neckCm = neck.toDouble(),
                                hipCm = hip.toDoubleOrNull(),
                            ))
                        }.onSuccess { bodyFat = "≈ ${it.estimatedBodyFatPct}%" }
                            .onFailure { bodyFat = context.getString(R.string.error_invalid_input) }
                    }
                }, enabled = waist.toDoubleOrNull() != null && neck.toDoubleOrNull() != null) {
                    Text(stringResource(R.string.estimate))
                }
                bodyFat?.let { Text(it, style = MaterialTheme.typography.headlineMedium) }
            }
        }

        // ---- weekly review
        Card {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(stringResource(R.string.weekly_review), style = MaterialTheme.typography.titleLarge)
                OutlinedButton(onClick = {
                    scope.launch {
                        safeCall { ApiProvider.init(context).weeklyReview() }.onSuccess { review = it }
                    }
                }) { Text(stringResource(R.string.generate_review)) }
                review?.let { r ->
                    r.avgWeightKg?.let { Text("${stringResource(R.string.weekly_average)}: $it kg") }
                    r.weightTrendKg?.let { Text("${stringResource(R.string.weight_trend)}: ${if (it > 0) "+" else ""}$it kg") }
                    if (r.wentWell.isNotEmpty()) {
                        Text(stringResource(R.string.went_well), style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary)
                        r.wentWell.forEach { Text("• ${reviewLabel(it, positive = true)}") }
                    }
                    if (r.needsAttention.isNotEmpty()) {
                        Text(stringResource(R.string.needs_attention), style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.error)
                        r.needsAttention.forEach { Text("• ${reviewLabel(it, positive = false)}") }
                    }
                    if (r.suggestions.isNotEmpty()) {
                        Text(stringResource(R.string.suggestions), style = MaterialTheme.typography.labelLarge)
                        r.suggestions.forEach { Text("• ${reviewLabel(it, positive = false)}") }
                    }
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

/** Maps backend review codes to localized text. `positive` disambiguates the two
 * codes ("logging_consistency", "protein_intake") that appear in both the
 * went-well and needs-attention lists with opposite meanings. */
@Composable
private fun reviewLabel(code: String, positive: Boolean): String = when (code) {
    "logging_consistency" -> if (positive) stringResource(R.string.review_logging_consistency_good)
        else stringResource(R.string.review_logging_consistency_bad)
    "no_logging" -> stringResource(R.string.review_no_logging)
    "protein_intake" -> if (positive) stringResource(R.string.review_protein_intake_good)
        else stringResource(R.string.review_protein_intake_bad)
    "weight_trend_on_track" -> stringResource(R.string.review_weight_trend_on_track)
    "weight_not_decreasing" -> stringResource(R.string.review_weight_not_decreasing)
    "weight_not_increasing" -> stringResource(R.string.review_weight_not_increasing)
    "increase_protein_foods" -> stringResource(R.string.review_increase_protein_foods)
    "weigh_more_mornings" -> stringResource(R.string.review_weigh_more_mornings)
    "log_more_days" -> stringResource(R.string.review_log_more_days)
    "start_logging" -> stringResource(R.string.review_start_logging)
    "review_targets_with_engine" -> stringResource(R.string.review_targets_with_engine)
    else -> code
}
