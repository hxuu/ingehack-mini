package com.ingehack.keepsecrets

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Ink = Color(0xFF0B0612)
val Night = Color(0xFF120A1C)
val Plum = Color(0xFF1E1130)
val Gold = Color(0xFFC9A227)
val GoldSoft = Color(0xFFE4C766)
val Violet = Color(0xFF8E6BB5)
val Parchment = Color(0xFFF2EAF7)
val Muted = Color(0xFFC9B8D8)
val Outline = Color(0xFF5A446E)
val Blood = Color(0xFF8E2F4A)

private val KeepSecretsColors = darkColorScheme(
    primary = Gold,
    onPrimary = Ink,
    primaryContainer = Color(0xFF3A2C0F),
    onPrimaryContainer = GoldSoft,
    secondary = Violet,
    onSecondary = Ink,
    secondaryContainer = Color(0xFF2A1B3D),
    onSecondaryContainer = Parchment,
    tertiary = Blood,
    onTertiary = Parchment,
    background = Ink,
    onBackground = Parchment,
    surface = Night,
    onSurface = Parchment,
    surfaceVariant = Plum,
    onSurfaceVariant = Muted,
    outline = Outline,
    outlineVariant = Color(0xFF3A2A4A),
    error = Color(0xFFCF6679),
    onError = Ink,
)

private val KeepSecretsTypography = Typography(
    displayLarge = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Normal,
        fontSize = 46.sp,
        lineHeight = 50.sp,
        letterSpacing = (-1).sp,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Normal,
        fontSize = 24.sp,
        lineHeight = 30.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 18.sp,
        lineHeight = 24.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 15.sp,
        lineHeight = 22.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    labelLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 11.sp,
        lineHeight = 16.sp,
        letterSpacing = 2.sp,
    ),
    labelMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 10.sp,
        lineHeight = 14.sp,
        letterSpacing = 1.4.sp,
    ),
)

@Composable
fun KeepSecretsTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = KeepSecretsColors,
        typography = KeepSecretsTypography,
        content = content,
    )
}
