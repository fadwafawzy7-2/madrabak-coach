package com.madrabak.coach.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.madrabak.coach.R
import com.madrabak.coach.data.api.ProfileUpdate
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.data.repo.safeCall
import com.madrabak.coach.util.ProfileValidator
import kotlinx.coroutines.launch

/** Wraps chips naturally to the available width instead of forcing fixed groups of 3,
 * so long labels (e.g. "المحافظة على الوزن") never overflow or crowd the row. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ChipRow(options: List<Pair<String, String>>, selected: String?, onSelect: (String) -> Unit) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        options.forEach { (value, label) ->
            FilterChip(selected = selected == value, onClick = { onSelect(value) }, label = { Text(label) })
        }
    }
}

/** One visually separated group: a title followed by its own chip set, wrapped in a
 * Card so it reads as its own block and never runs into the section above/below it. */
@Composable
private fun ChipSection(
    title: String,
    options: List<Pair<String, String>>,
    selected: String?,
    onSelect: (String) -> Unit,
) {
    Card {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            ChipRow(options, selected, onSelect)
        }
    }
}

@Composable
fun OnboardingScreen(onDone: () -> Unit, isEditing: Boolean = false, onBack: (() -> Unit)? = null) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var age by remember { mutableStateOf("") }
    var sex by remember { mutableStateOf<String?>(null) }
    var height by remember { mutableStateOf("") }
    var weight by remember { mutableStateOf("") }
    var sport by remember { mutableStateOf<String?>(null) }
    var goal by remember { mutableStateOf<String?>(null) }
    var activity by remember { mutableStateOf<String?>(null) }
    var trainingDays by remember { mutableStateOf("3") }
    var trainingMin by remember { mutableStateOf("60") }
    var intensity by remember { mutableStateOf("moderate") }
    var matches by remember { mutableStateOf("0") }
    var budget by remember { mutableStateOf("medium") }
    var saving by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf(false) }

    // When editing an existing profile, prefill with the saved values instead of blanks.
    if (isEditing) {
        LaunchedEffect(Unit) {
            safeCall { ApiProvider.init(context).getProfile() }.onSuccess { p ->
                age = p.age?.toString() ?: ""
                sex = p.sex
                height = p.heightCm?.toString() ?: ""
                weight = p.weightKg?.toString() ?: ""
                sport = p.sport
                goal = p.primaryGoal
                activity = p.activityLevel
                trainingDays = p.trainingDaysPerWeek?.toString() ?: trainingDays
                trainingMin = p.trainingDurationMin?.toString() ?: trainingMin
                intensity = p.trainingIntensity ?: intensity
                matches = p.matchesPerWeek?.toString() ?: matches
                budget = p.budgetTier ?: budget
            }
        }
    }

    val sports = listOf(
        "bodybuilding" to stringResource(R.string.sport_bodybuilding),
        "strength" to stringResource(R.string.sport_strength),
        "calisthenics" to stringResource(R.string.sport_calisthenics),
        "running" to stringResource(R.string.sport_running),
        "football" to stringResource(R.string.sport_football),
        "non_athlete" to stringResource(R.string.sport_non_athlete),
    )
    val goals = listOf(
        "lose_weight" to stringResource(R.string.goal_lose_weight),
        "lose_fat" to stringResource(R.string.goal_lose_fat),
        "maintain" to stringResource(R.string.goal_maintain),
        "gain_weight" to stringResource(R.string.goal_gain_weight),
        "gain_muscle" to stringResource(R.string.goal_gain_muscle),
        "recomposition" to stringResource(R.string.goal_recomposition),
        "increase_strength" to stringResource(R.string.goal_increase_strength),
        "athletic_performance" to stringResource(R.string.goal_athletic_performance),
        "running_performance" to stringResource(R.string.goal_running_performance),
        "calisthenics_performance" to stringResource(R.string.goal_calisthenics_performance),
    )
    // Only the goals that actually make sense for each sport — a bodybuilder
    // isn't offered "running performance", a runner isn't offered "increase
    // strength" as a primary goal, etc. Kept in a map so the list is easy to
    // tune later without touching the filtering logic below.
    val goalsBySport = mapOf(
        "bodybuilding" to listOf("lose_fat", "gain_muscle", "recomposition", "gain_weight", "maintain"),
        "strength" to listOf("increase_strength", "gain_muscle", "gain_weight", "recomposition", "maintain"),
        "calisthenics" to listOf("calisthenics_performance", "lose_fat", "recomposition", "gain_muscle", "maintain"),
        "running" to listOf("running_performance", "lose_fat", "lose_weight", "maintain"),
        "football" to listOf("athletic_performance", "lose_fat", "gain_muscle", "increase_strength", "maintain"),
        "non_athlete" to listOf("lose_weight", "lose_fat", "maintain", "gain_weight", "recomposition"),
    )
    val allowedGoalKeys = sport?.let { goalsBySport[it] }
    val filteredGoals = if (allowedGoalKeys != null) goals.filter { it.first in allowedGoalKeys } else goals
    val activities = listOf(
        "sedentary" to stringResource(R.string.activity_sedentary),
        "light" to stringResource(R.string.activity_light),
        "moderate" to stringResource(R.string.activity_moderate),
        "high" to stringResource(R.string.activity_high),
    )

    val valid = ProfileValidator.isValid(
        age.toIntOrNull(), sex, height.toDoubleOrNull(), weight.toDoubleOrNull(), sport, goal, activity,
    )

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            if (onBack != null) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.back))
                }
                Spacer(Modifier.width(4.dp))
            }
            Text(
                stringResource(if (isEditing) R.string.edit_profile else R.string.onboarding_title),
                style = MaterialTheme.typography.headlineMedium,
            )
        }

        Card {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row {
                    OutlinedTextField(value = age, onValueChange = { age = it.filter(Char::isDigit) },
                        label = { Text(stringResource(R.string.age)) }, modifier = Modifier.weight(1f))
                    Spacer(Modifier.width(12.dp))
                    OutlinedTextField(value = height, onValueChange = { height = it },
                        label = { Text(stringResource(R.string.height_cm)) }, modifier = Modifier.weight(1f))
                    Spacer(Modifier.width(12.dp))
                    OutlinedTextField(value = weight, onValueChange = { weight = it },
                        label = { Text(stringResource(R.string.weight_kg)) }, modifier = Modifier.weight(1f))
                }
                Text(stringResource(R.string.sex), style = MaterialTheme.typography.labelLarge)
                ChipRow(listOf("male" to stringResource(R.string.male), "female" to stringResource(R.string.female)), sex) { sex = it }
            }
        }

        ChipSection(stringResource(R.string.sport), sports, sport) {
            sport = it
            if (goal != null && goal !in (goalsBySport[it] ?: emptyList())) goal = null
        }

        ChipSection(stringResource(R.string.goal), filteredGoals, goal) { goal = it }

        ChipSection(stringResource(R.string.activity_level), activities, activity) { activity = it }

        Card {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row {
                    OutlinedTextField(value = trainingDays, onValueChange = { trainingDays = it.filter(Char::isDigit) },
                        label = { Text(stringResource(R.string.training_days)) }, modifier = Modifier.weight(1f))
                    Spacer(Modifier.width(12.dp))
                    OutlinedTextField(value = trainingMin, onValueChange = { trainingMin = it.filter(Char::isDigit) },
                        label = { Text(stringResource(R.string.training_duration)) }, modifier = Modifier.weight(1f))
                }
                Text(stringResource(R.string.training_intensity), style = MaterialTheme.typography.labelLarge)
                ChipRow(listOf(
                    "low" to stringResource(R.string.intensity_low),
                    "moderate" to stringResource(R.string.intensity_moderate),
                    "high" to stringResource(R.string.intensity_high),
                ), intensity) { intensity = it }

                if (sport == "football") {
                    OutlinedTextField(value = matches, onValueChange = { matches = it.filter(Char::isDigit) },
                        label = { Text(stringResource(R.string.matches_per_week)) }, modifier = Modifier.fillMaxWidth())
                }
            }
        }

        ChipSection(
            stringResource(R.string.budget),
            listOf(
                "low" to stringResource(R.string.budget_low),
                "medium" to stringResource(R.string.budget_medium),
                "high" to stringResource(R.string.budget_high),
            ),
            budget,
        ) { budget = it }

        if (error) Text(stringResource(R.string.error_generic), color = MaterialTheme.colorScheme.error)

        Button(
            onClick = {
                saving = true; error = false
                scope.launch {
                    val api = ApiProvider.init(context)
                    val result = safeCall {
                        api.updateProfile(ProfileUpdate(
                            age = age.toInt(), sex = sex, heightCm = height.toDouble(),
                            weightKg = weight.toDouble(), sport = sport, primaryGoal = goal,
                            activityLevel = activity,
                            trainingDaysPerWeek = trainingDays.toIntOrNull() ?: 0,
                            trainingDurationMin = trainingMin.toIntOrNull() ?: 0,
                            trainingIntensity = intensity,
                            matchesPerWeek = matches.toIntOrNull() ?: 0,
                            budgetTier = budget,
                            onboardingCompleted = true,
                        ))
                        api.recalculateTarget()
                    }
                    saving = false
                    result.onSuccess { onDone() }.onFailure { error = true }
                }
            },
            enabled = valid && !saving,
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) { Text(stringResource(R.string.finish)) }
        Spacer(Modifier.height(24.dp))
    }
}
