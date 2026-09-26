import java.util.Base64

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
}

android {
    namespace = "com.madrabak.coach"
    compileSdk = 34

    // Pass -PAPI_BASE_URL=https://your-backend-url/api/ at build time to point
    // the app at your deployed backend. Falls back to the emulator address if
    // not provided, so a plain `./gradlew assembleDebug` still works in an emulator.
    val apiBaseUrl = (project.findProperty("API_BASE_URL") as String?) ?: "http://10.0.2.2:8000/api/"

    defaultConfig {
        applicationId = "com.madrabak.coach"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
        // Backend base URL is configuration, NOT a secret. No API keys live in the app.
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
        vectorDrawables { useSupportLibrary = true }
    }

    // Release signing: reads the keystore from a GitHub Actions secret so every
    // build is signed with the SAME certificate (required for Google Sign-In's
    // SHA-1 fingerprint to keep matching). Falls back to the debug key when the
    // secret isn't set (e.g. a local `assembleRelease`), so local builds never break.
    val releaseKeystoreBase64 = System.getenv("ANDROID_KEYSTORE_BASE64")
    signingConfigs {
        if (!releaseKeystoreBase64.isNullOrBlank()) {
            create("release") {
                val decodedKeystore = File(layout.buildDirectory.get().asFile, "release.keystore")
                decodedKeystore.parentFile.mkdirs()
                decodedKeystore.writeBytes(Base64.getDecoder().decode(releaseKeystoreBase64))
                storeFile = decodedKeystore
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = if (!releaseKeystoreBase64.isNullOrBlank())
                signingConfigs.getByName("release")
            else
                signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.14" }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.06.00")
    implementation(composeBom)
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.3")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("androidx.datastore:datastore-preferences:1.1.1")

    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:1.0.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // Google Play Billing (subscriptions)
    implementation("com.android.billingclient:billing-ktx:7.0.0")

    // Google Sign-In (Credential Manager — shows the device's Google accounts)
    implementation("androidx.credentials:credentials:1.3.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.3.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")

    // Unit tests
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
}
