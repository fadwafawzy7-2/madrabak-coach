package com.madrabak.coach.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Credentials(val email: String, val password: String)

@Serializable
data class AuthResponse(@SerialName("user_id") val userId: String, val token: String)

@Serializable
data class Profile(
    @SerialName("user_id") val userId: String? = null,
    @SerialName("display_name") val displayName: String? = null,
    val age: Int? = null,
    val sex: String? = null,
    @SerialName("height_cm") val heightCm: Double? = null,
    @SerialName("weight_kg") val weightKg: Double? = null,
    val sport: String? = null,
    @SerialName("primary_goal") val primaryGoal: String? = null,
    @SerialName("activity_level") val activityLevel: String? = null,
    @SerialName("training_days_per_week") val trainingDaysPerWeek: Int? = null,
    @SerialName("training_duration_min") val trainingDurationMin: Int? = null,
    @SerialName("training_intensity") val trainingIntensity: String? = null,
    @SerialName("matches_per_week") val matchesPerWeek: Int? = null,
    @SerialName("matches_replace_training_day") val matchesReplaceTrainingDay: Boolean? = null,
    @SerialName("budget_tier") val budgetTier: String? = null,
    val language: String? = null,
    @SerialName("units_system") val unitsSystem: String? = null,
    @SerialName("onboarding_completed") val onboardingCompleted: Boolean? = null,
    @SerialName("notifications_enabled") val notificationsEnabled: Boolean? = null,
)

@Serializable
data class ProfileUpdate(
    val age: Int? = null,
    val sex: String? = null,
    @SerialName("height_cm") val heightCm: Double? = null,
    @SerialName("weight_kg") val weightKg: Double? = null,
    val sport: String? = null,
    @SerialName("primary_goal") val primaryGoal: String? = null,
    @SerialName("activity_level") val activityLevel: String? = null,
    @SerialName("training_days_per_week") val trainingDaysPerWeek: Int? = null,
    @SerialName("training_duration_min") val trainingDurationMin: Int? = null,
    @SerialName("training_intensity") val trainingIntensity: String? = null,
    @SerialName("matches_per_week") val matchesPerWeek: Int? = null,
    @SerialName("budget_tier") val budgetTier: String? = null,
    val language: String? = null,
    @SerialName("onboarding_completed") val onboardingCompleted: Boolean? = null,
    @SerialName("notifications_enabled") val notificationsEnabled: Boolean? = null,
)

@Serializable
data class MacroSet(
    val kcal: Double = 0.0,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("carbs_g") val carbsG: Double = 0.0,
    @SerialName("fat_g") val fatG: Double = 0.0,
    @SerialName("fiber_g") val fiberG: Double? = null,
)

@Serializable
data class NutritionTarget(
    @SerialName("target_kcal") val targetKcal: Int,
    @SerialName("protein_g") val proteinG: Int,
    @SerialName("carbs_g") val carbsG: Int,
    @SerialName("fat_g") val fatG: Int,
    @SerialName("bmr_kcal") val bmrKcal: Int? = null,
    @SerialName("tdee_kcal") val tdeeKcal: Int? = null,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class TargetSummary(
    val kcal: Int,
    @SerialName("protein_g") val proteinG: Int,
    @SerialName("carbs_g") val carbsG: Int,
    @SerialName("fat_g") val fatG: Int,
)

@Serializable
data class Dashboard(
    val target: TargetSummary? = null,
    val consumed: MacroSet = MacroSet(),
    val remaining: MacroSet? = null,
    val meals: List<Meal> = emptyList(),
    @SerialName("morning_weight_kg") val morningWeightKg: Double? = null,
    val sport: String? = null,
)

@Serializable
data class Food(
    val id: String,
    val name: String,
    @SerialName("kcal_per_100g") val kcalPer100g: Double,
    @SerialName("protein_per_100g") val proteinPer100g: Double,
    @SerialName("carbs_per_100g") val carbsPer100g: Double,
    @SerialName("fat_per_100g") val fatPer100g: Double,
    @SerialName("confidence_level") val confidenceLevel: String,
)

@Serializable
data class FoodSearchResponse(val results: List<Food>)

@Serializable
data class MealItemIn(
    @SerialName("food_id") val foodId: String? = null,
    @SerialName("food_name") val foodName: String? = null,
    val quantity: Double,
    val unit: String = "g",
    @SerialName("is_estimated") val isEstimated: Boolean = false,
)

@Serializable
data class MealIn(
    @SerialName("meal_type") val mealType: String,
    val source: String = "manual",
    val items: List<MealItemIn>,
)

@Serializable
data class MealItem(
    val id: String,
    @SerialName("food_name") val foodName: String,
    @SerialName("quantity_g") val quantityG: Double,
    val kcal: Double,
    @SerialName("protein_g") val proteinG: Double,
    @SerialName("carbs_g") val carbsG: Double,
    @SerialName("fat_g") val fatG: Double,
)

@Serializable
data class Meal(
    val id: String,
    @SerialName("meal_type") val mealType: String,
    @SerialName("eaten_at") val eatenAt: String,
    val source: String,
    val items: List<MealItem> = emptyList(),
    val totals: MacroSet = MacroSet(),
)

@Serializable
data class DayMeals(val meals: List<Meal>, val totals: MacroSet)

@Serializable
data class DraftItem(
    val matched: Boolean,
    @SerialName("food_id") val foodId: String? = null,
    @SerialName("food_name") val foodName: String? = null,
    @SerialName("detected_name") val detectedName: String,
    @SerialName("estimated_grams") val estimatedGrams: Double,
    val kcal: Double? = null,
    @SerialName("protein_g") val proteinG: Double? = null,
)

@Serializable
data class PhotoAnalysis(@SerialName("draft_items") val draftItems: List<DraftItem>)

@Serializable
data class MeasurementIn(
    val kind: String,
    val value: Double,
    @SerialName("is_morning") val isMorning: Boolean = false,
)

@Serializable
data class WeeklyAvg(
    @SerialName("week_start") val weekStart: String,
    @SerialName("avg_kg") val avgKg: Double,
    val count: Int,
)

@Serializable
data class MeasurementPoint(
    val id: String,
    @SerialName("measured_at") val measuredAt: String,
    val value: Double,
    @SerialName("is_morning") val isMorning: Boolean,
)

@Serializable
data class WeightSummary(
    val points: List<MeasurementPoint> = emptyList(),
    @SerialName("weekly_averages") val weeklyAverages: List<WeeklyAvg> = emptyList(),
    @SerialName("week_over_week_kg") val weekOverWeekKg: Double? = null,
)

@Serializable
data class BodyFatIn(
    @SerialName("waist_cm") val waistCm: Double,
    @SerialName("neck_cm") val neckCm: Double,
    @SerialName("hip_cm") val hipCm: Double? = null,
)

@Serializable
data class BodyFatResult(
    @SerialName("estimated_body_fat_pct") val estimatedBodyFatPct: Double,
    val disclaimer: String,
)

@Serializable
data class WeeklyReview(
    @SerialName("week_start") val weekStart: String,
    @SerialName("avg_weight_kg") val avgWeightKg: Double? = null,
    @SerialName("weight_trend_kg") val weightTrendKg: Double? = null,
    @SerialName("days_logged") val daysLogged: Int = 0,
    @SerialName("avg_kcal") val avgKcal: Double? = null,
    @SerialName("avg_protein_g") val avgProteinG: Double? = null,
    @SerialName("went_well") val wentWell: List<String> = emptyList(),
    @SerialName("needs_attention") val needsAttention: List<String> = emptyList(),
    val suggestions: List<String> = emptyList(),
)

@Serializable
data class ChatIn(val message: String)

@Serializable
data class ChatResponse(val reply: String, val blocked: Boolean = false)

@Serializable
data class ChatMessage(val role: String, val content: String, @SerialName("created_at") val createdAt: String? = null)

@Serializable
data class ChatHistory(val messages: List<ChatMessage>)

@Serializable
data class SuggestionResponse(val suggestion: String)

@Serializable
data class IngredientsIn(val ingredients: List<String>)

@Serializable
data class SubscriptionStatus(
    val status: String,
    @SerialName("trial_ends_at") val trialEndsAt: String,
    @SerialName("has_access") val hasAccess: Boolean,
    @SerialName("price_usd_month") val priceUsdMonth: Double,
)

@Serializable
data class PurchaseIn(
    @SerialName("product_id") val productId: String,
    @SerialName("purchase_token") val purchaseToken: String,
)
