package com.madrabak.coach.data.repo

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.madrabak.coach.BuildConfig
import com.madrabak.coach.data.api.ApiService
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

private val Context.dataStore by preferencesDataStore(name = "session")

/** Session store: keeps the auth token (never logged). */
class SessionStore(private val context: Context) {
    private val tokenKey = stringPreferencesKey("token")
    private val langKey = stringPreferencesKey("language")

    val token: Flow<String?> = context.dataStore.data.map { it[tokenKey] }
    val language: Flow<String?> = context.dataStore.data.map { it[langKey] }

    suspend fun setToken(token: String?) {
        context.dataStore.edit { prefs ->
            if (token == null) prefs.remove(tokenKey) else prefs[tokenKey] = token
        }
    }

    suspend fun setLanguage(lang: String) {
        context.dataStore.edit { it[langKey] = lang }
    }

    fun tokenBlocking(): String? = runBlocking { token.first() }
}

/** ApiProvider: single Retrofit instance with auth header injection. */
object ApiProvider {
    @Volatile private var api: ApiService? = null
    @Volatile private var session: SessionStore? = null

    fun init(context: Context): ApiService {
        val existing = api
        if (existing != null) return existing
        synchronized(this) {
            val cached = api
            if (cached != null) return cached
            val store = SessionStore(context.applicationContext)
            session = store
            val client = OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .addInterceptor { chain ->
                    val token = store.tokenBlocking()
                    val request = if (token != null) {
                        chain.request().newBuilder().header("Authorization", "Bearer $token").build()
                    } else chain.request()
                    chain.proceed(request)
                }
                .build()
            val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
            val created = Retrofit.Builder()
                .baseUrl(BuildConfig.API_BASE_URL)
                .client(client)
                .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
                .build()
                .create(ApiService::class.java)
            api = created
            return created
        }
    }

    fun sessionStore(context: Context): SessionStore {
        return session ?: SessionStore(context.applicationContext).also { session = it }
    }
}

/** Maps HTTP failures to stable UI error codes. */
sealed class ApiError(message: String) : Exception(message) {
    object NoInternet : ApiError("no_internet")
    object Unauthorized : ApiError("unauthorized")
    object LimitReached : ApiError("limit_reached")
    object AiUnavailable : ApiError("ai_unavailable")
    object SubscriptionExpired : ApiError("subscription_expired")
    class Validation(val code: String) : ApiError(code)
    object Generic : ApiError("generic")
}

suspend fun <T> safeCall(block: suspend () -> T): Result<T> = try {
    Result.success(block())
} catch (e: retrofit2.HttpException) {
    Result.failure(
        when (e.code()) {
            401 -> ApiError.Unauthorized
            402 -> ApiError.SubscriptionExpired
            422 -> ApiError.Validation("invalid_input")
            429 -> ApiError.LimitReached
            503 -> ApiError.AiUnavailable
            else -> ApiError.Generic
        }
    )
} catch (e: java.io.IOException) {
    Result.failure(ApiError.NoInternet)
} catch (e: Exception) {
    Result.failure(ApiError.Generic)
}
