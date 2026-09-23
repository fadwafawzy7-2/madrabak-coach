package com.madrabak.coach.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val Emerald = Color(0xFF0E9F7E)
private val EmeraldDark = Color(0xFF0B7A61)
private val Amber = Color(0xFFF59E0B)

private val LightColors = lightColorScheme(
    primary = Emerald,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD3F3EA),
    onPrimaryContainer = Color(0xFF063D31),
    secondary = Amber,
    onSecondary = Color.White,
    background = Color(0xFFF7FAF9),
    surface = Color.White,
    surfaceVariant = Color(0xFFEDF3F1),
    onBackground = Color(0xFF15211E),
    onSurface = Color(0xFF15211E),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF3FCBA8),
    onPrimary = Color(0xFF00382B),
    primaryContainer = EmeraldDark,
    onPrimaryContainer = Color(0xFFC5F2E5),
    secondary = Amber,
    background = Color(0xFF0E1513),
    surface = Color(0xFF161F1C),
    surfaceVariant = Color(0xFF1F2B27),
    onBackground = Color(0xFFE2EAE7),
    onSurface = Color(0xFFE2EAE7),
)

private val AppTypography = Typography(
    displayLarge = TextStyle(fontSize = 48.sp, fontWeight = FontWeight.Bold),
    headlineMedium = TextStyle(fontSize = 26.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 20.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 16.sp),
    bodyMedium = TextStyle(fontSize = 14.sp),
    labelLarge = TextStyle(fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
)

@Composable
fun CoachTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}
