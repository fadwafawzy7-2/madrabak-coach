package com.madrabak.coach.data.api

import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/** All requests are proxied through the backend — no AI keys exist in the app. */
interface ApiService {
    @POST("auth/register")
    suspend fun register(@Body body: Credentials): AuthResponse

    @POST("auth/login")
    suspend fun login(@Body body: Credentials): AuthResponse

    @POST("auth/google")
    suspend fun googleAuth(@Body body: GoogleAuthIn): AuthResponse

    @GET("profile")
    suspend fun getProfile(): Profile

    @PUT("profile")
    suspend fun updateProfile(@Body body: ProfileUpdate): Profile

    @DELETE("account")
    suspend fun deleteAccount()

    @DELETE("account/data")
    suspend fun deleteData()

    @POST("nutrition/targets/recalculate")
    suspend fun recalculateTarget(): NutritionTarget

    @GET("dashboard/today")
    suspend fun dashboard(): Dashboard

    @GET("foods/search")
    suspend fun searchFoods(@Query("q") query: String, @Query("language") language: String? = null): FoodSearchResponse

    @POST("meals")
    suspend fun createMeal(@Body body: MealIn): Meal

    @GET("meals/day/{day}")
    suspend fun mealsForDay(@Path("day") day: String): DayMeals

    @DELETE("meals/{id}")
    suspend fun deleteMeal(@Path("id") id: String)

    @Multipart
    @POST("meals/analyze-photo")
    suspend fun analyzePhoto(
        @Part image: MultipartBody.Part,
        @Part("language") language: okhttp3.RequestBody,
    ): PhotoAnalysis

    @POST("progress/measurements")
    suspend fun logMeasurement(@Body body: MeasurementIn)

    @GET("progress/weight-summary")
    suspend fun weightSummary(): WeightSummary

    @POST("progress/body-fat")
    suspend fun bodyFat(@Body body: BodyFatIn): BodyFatResult

    @POST("progress/weekly-review")
    suspend fun weeklyReview(): WeeklyReview

    @POST("coach/chat")
    suspend fun chat(@Body body: ChatIn): ChatResponse

    @GET("coach/history")
    suspend fun chatHistory(): ChatHistory

    @POST("coach/what-to-eat")
    suspend fun whatToEat(): SuggestionResponse

    @POST("coach/ingredients")
    suspend fun ingredients(@Body body: IngredientsIn): SuggestionResponse

    @POST("coach/save-my-day")
    suspend fun saveMyDay(): SuggestionResponse

    @GET("subscription")
    suspend fun subscription(): SubscriptionStatus

    @POST("subscription/verify")
    suspend fun verifyPurchase(@Body body: PurchaseIn): SubscriptionStatus
}
