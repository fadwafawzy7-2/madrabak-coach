package com.madrabak.coach.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.shape.RoundedCornerShape

private val Emerald = Color(0xFF0B9D77)
private val EmeraldDeep = Color(0xFF066B52)
private val EmeraldSoft = Color(0xFFD7F4E9)
private val Coral = Color(0xFFFF6B4A)
private val CoralSoft = Color(0xFFFFE2D9)
private val Violet = Color(0xFF6C63FF)
private val VioletSoft = Color(0xFFE7E5FF)
private val InkLight = Color(0xFF12211D)
private val InkDark = Color(0xFFE7F1ED)

private val LightColors = lightColorScheme(
    primary = Emerald,
    onPrimary = Color.White,
    primaryContainer = EmeraldSoft,
    onPrimaryContainer = Color(0xFF063D31),
    secondary = Coral,
    onSecondary = Color.White,
    secondaryContainer = CoralSoft,
    onSecondaryContainer = Color(0xFF5C2210),
    tertiary = Violet,
    onTertiary = Color.White,
    tertiaryContainer = VioletSoft,
    onTertiaryContainer = Color(0xFF241F6B),
    background = Color(0xFFFAFBFA),
    surface = Color.White,
    surfaceVariant = Color(0xFFEFF4F2),
    onSurfaceVariant = Color(0xFF44534D),
    outline = Color(0xFFB9C6C0),
    error = Color(0xFFDC3545),
    onBackground = InkLight,
    onSurface = InkLight,
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF44D6AC),
    onPrimary = Color(0xFF00382B),
    primaryContainer = EmeraldDeep,
    onPrimaryContainer = Color(0xFFC5F2E5),
    secondary = Color(0xFFFF8B6C),
    onSecondary = Color(0xFF4A1B0C),
    secondaryContainer = Color(0xFF6B2A16),
    onSecondaryContainer = CoralSoft,
    tertiary = Color(0xFFB2ABFF),
    onTertiary = Color(0xFF2A2470),
    tertiaryContainer = Color(0xFF3D3690),
    onTertiaryContainer = VioletSoft,
    background = Color(0xFF0D1512),
    surface = Color(0xFF151F1B),
    surfaceVariant = Color(0xFF212D28),
    onSurfaceVariant = Color(0xFFBFCEC8),
    outline = Color(0xFF3E4D47),
    onBackground = InkDark,
    onSurface = InkDark,
)

private val AppTypography = Typography(
    displayLarge = TextStyle(fontSize = 44.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.5).sp),
    headlineLarge = TextStyle(fontSize = 32.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.3).sp),
    headlineMedium = TextStyle(fontSize = 26.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 21.sp, fontWeight = FontWeight.Bold),
    titleMedium = TextStyle(fontSize = 17.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    labelLarge = TextStyle(fontSize = 15.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 0.2.sp),
    labelMedium = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.Medium),
)

private val AppShapes = Shapes(
    extraSmall = RoundedCornerShape(10.dp),
    small = RoundedCornerShape(14.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(32.dp),
)

@Composable
fun CoachTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = AppTypography,
        shapes = AppShapes,
        content = content,
    )
}
