package com.madrabak.coach.ui.screens

import android.graphics.Bitmap
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import com.madrabak.coach.data.api.DraftItem
import com.madrabak.coach.data.api.Food
import com.madrabak.coach.data.api.Meal
import com.madrabak.coach.data.api.MealIn
import com.madrabak.coach.data.api.MealItemIn
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.data.repo.safeCall
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.time.LocalDate

private data class PendingItem(val foodId: String?, val name: String, var grams: String, val estimated: Boolean)

@Composable
fun FoodScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var mealType by remember { mutableStateOf("lunch") }
    var query by remember { mutableStateOf("") }
    var results by remember { mutableStateOf<List<Food>>(emptyList()) }
    val pending = remember { mutableStateListOf<PendingItem>() }
    var todayMeals by remember { mutableStateOf<List<Meal>>(emptyList()) }
    var analyzing by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }
    var source by remember { mutableStateOf("manual") }

    fun refreshDay() {
        scope.launch {
            safeCall { ApiProvider.init(context).mealsForDay(LocalDate.now().toString()) }
                .onSuccess { todayMeals = it.meals }
        }
    }
    LaunchedEffect(Unit) { refreshDay() }

    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicturePreview()) { bitmap ->
        if (bitmap != null) {
            analyzing = true; message = null
            scope.launch {
                val stream = ByteArrayOutputStream()
                bitmap.compress(Bitmap.CompressFormat.JPEG, 85, stream)
                val body = stream.toByteArray().toRequestBody("image/jpeg".toMediaType())
                val part = MultipartBody.Part.createFormData("image", "meal.jpg", body)
                val lang = "ar".toRequestBody("text/plain".toMediaType())
                safeCall { ApiProvider.init(context).analyzePhoto(part, lang) }
                    .onSuccess { analysis ->
                        source = "photo"
                        analysis.draftItems.forEach { d: DraftItem ->
                            pending.add(PendingItem(d.foodId, d.foodName ?: d.detectedName,
                                d.estimatedGrams.toInt().toString(), estimated = true))
                        }
                        message = context.getString(R.string.photo_estimate_note)
                    }
                    .onFailure { message = context.getString(R.string.error_ai_unavailable) }
                analyzing = false
            }
        }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(stringResource(R.string.log_meal), style = MaterialTheme.typography.headlineMedium)
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(
                    "breakfast" to stringResource(R.string.meal_breakfast),
                    "lunch" to stringResource(R.string.meal_lunch),
                    "dinner" to stringResource(R.string.meal_dinner),
                    "snack" to stringResource(R.string.meal_snack),
                ).forEach { (value, label) ->
                    FilterChip(selected = mealType == value, onClick = { mealType = value }, label = { Text(label) })
                }
            }
        }
        item {
            Button(onClick = { cameraLauncher.launch(null) }, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Filled.PhotoCamera, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(stringResource(R.string.action_photo_meal))
            }
        }
        if (analyzing) item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(Modifier.height(20.dp))
                Spacer(Modifier.width(8.dp))
                Text(stringResource(R.string.photo_analyzing))
            }
        }
        message?.let { m -> item { Text(m, color = MaterialTheme.colorScheme.secondary) } }

        item {
            OutlinedTextField(
                value = query,
                onValueChange = {
                    query = it
                    if (it.length >= 2) scope.launch {
                        safeCall { ApiProvider.init(context).searchFoods(it) }
                            .onSuccess { r -> results = r.results }
                    } else results = emptyList()
                },
                label = { Text(stringResource(R.string.search_food)) },
                modifier = Modifier.fillMaxWidth(),
            )
        }
        items(results.take(6)) { food ->
            Card(Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text(food.name, style = MaterialTheme.typography.labelLarge)
                        Text("${food.kcalPer100g.toInt()} ${stringResource(R.string.kcal_unit)}/100${stringResource(R.string.gram_unit)}",
                            style = MaterialTheme.typography.bodyMedium)
                    }
                    OutlinedButton(onClick = {
                        pending.add(PendingItem(food.id, food.name, "100", estimated = false))
                        query = ""; results = emptyList()
                    }) { Text(stringResource(R.string.add_item)) }
                }
            }
        }

        // pending items (editable before confirm — required for photo drafts)
        items(pending.toList()) { item ->
            Card(Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(item.name, style = MaterialTheme.typography.labelLarge)
                        if (item.foodId == null) {
                            Text(stringResource(R.string.unmatched_food), color = MaterialTheme.colorScheme.error,
                                style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                    OutlinedTextField(
                        value = item.grams,
                        onValueChange = { new ->
                            val idx = pending.indexOf(item)
                            if (idx >= 0) pending[idx] = item.copy(grams = new.filter(Char::isDigit))
                        },
                        label = { Text(stringResource(R.string.quantity_g)) },
                        modifier = Modifier.width(120.dp),
                        singleLine = true,
                    )
                    IconButton(onClick = { pending.remove(item) }) {
                        Icon(Icons.Filled.Delete, contentDescription = stringResource(R.string.cancel))
                    }
                }
            }
        }

        if (pending.isNotEmpty()) item {
            Button(
                onClick = {
                    scope.launch {
                        val items = pending.filter { it.foodId != null && (it.grams.toDoubleOrNull() ?: 0.0) > 0 }
                            .map { MealItemIn(foodId = it.foodId, quantity = it.grams.toDouble(), isEstimated = it.estimated) }
                        if (items.isEmpty()) return@launch
                        safeCall { ApiProvider.init(context).createMeal(MealIn(mealType, source, items)) }
                            .onSuccess { pending.clear(); source = "manual"; message = null; refreshDay() }
                            .onFailure { message = context.getString(R.string.error_generic) }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) { Text(stringResource(R.string.confirm_meal)) }
        }

        item { Text(stringResource(R.string.todays_meals), style = MaterialTheme.typography.titleLarge) }
        if (todayMeals.isEmpty()) item { Text(stringResource(R.string.no_meals_yet)) }
        items(todayMeals) { meal ->
            Card(Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text(mealTypeLabel(meal.mealType), style = MaterialTheme.typography.labelLarge)
                        Text(meal.items.joinToString { it.foodName }, style = MaterialTheme.typography.bodyMedium)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("${meal.totals.kcal.toInt()} ${stringResource(R.string.kcal_unit)}",
                            style = MaterialTheme.typography.labelLarge)
                        IconButton(onClick = {
                            scope.launch {
                                safeCall { ApiProvider.init(context).deleteMeal(meal.id) }.onSuccess { refreshDay() }
                            }
                        }) { Icon(Icons.Filled.Delete, contentDescription = null) }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
private fun mealTypeLabel(type: String): String = when (type) {
    "breakfast" -> stringResource(R.string.meal_breakfast)
    "lunch" -> stringResource(R.string.meal_lunch)
    "dinner" -> stringResource(R.string.meal_dinner)
    else -> stringResource(R.string.meal_snack)
}
