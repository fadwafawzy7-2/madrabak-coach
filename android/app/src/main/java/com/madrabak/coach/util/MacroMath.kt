package com.madrabak.coach.util

/** Small pure helpers used by UI — unit tested. */
object MacroMath {
    /** Progress ratio clamped to 0..1; safe when target is 0. */
    fun progress(consumed: Double, target: Double): Float {
        if (target <= 0.0) return 0f
        return (consumed / target).coerceIn(0.0, 1.0).toFloat()
    }

    fun remaining(target: Double, consumed: Double): Double = target - consumed

    /** kg <-> lb conversions at the input/output boundary only. */
    fun kgToLb(kg: Double): Double = kg * 2.2046226218
    fun lbToKg(lb: Double): Double = lb / 2.2046226218
    fun cmToInch(cm: Double): Double = cm * 0.3937007874
    fun inchToCm(inch: Double): Double = inch / 0.3937007874
}

object ProfileValidator {
    fun isValid(
        age: Int?, sex: String?, heightCm: Double?, weightKg: Double?,
        sport: String?, goal: String?, activity: String?,
    ): Boolean {
        if (age == null || age < 13 || age > 100) return false
        if (sex !in listOf("male", "female")) return false
        if (heightCm == null || heightCm < 100 || heightCm > 250) return false
        if (weightKg == null || weightKg < 30 || weightKg > 300) return false
        if (sport.isNullOrBlank() || goal.isNullOrBlank() || activity.isNullOrBlank()) return false
        return true
    }
}
