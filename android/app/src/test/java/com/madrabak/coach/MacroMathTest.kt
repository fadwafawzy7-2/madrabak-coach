package com.madrabak.coach

import com.madrabak.coach.util.MacroMath
import com.madrabak.coach.util.ProfileValidator
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MacroMathTest {
    @Test
    fun progressClampsToOne() {
        assertEquals(1f, MacroMath.progress(3000.0, 2000.0))
    }

    @Test
    fun progressZeroTargetIsSafe() {
        assertEquals(0f, MacroMath.progress(500.0, 0.0))
    }

    @Test
    fun progressNormal() {
        assertEquals(0.5f, MacroMath.progress(1000.0, 2000.0), 0.001f)
    }

    @Test
    fun remainingCanBeNegative() {
        assertEquals(-200.0, MacroMath.remaining(1800.0, 2000.0), 0.001)
    }

    @Test
    fun unitConversionsRoundTrip() {
        assertEquals(80.0, MacroMath.lbToKg(MacroMath.kgToLb(80.0)), 0.0001)
        assertEquals(178.0, MacroMath.inchToCm(MacroMath.cmToInch(178.0)), 0.0001)
        assertEquals(220.46, MacroMath.kgToLb(100.0), 0.01)
    }
}

class ProfileValidatorTest {
    @Test
    fun validProfilePasses() {
        assertTrue(ProfileValidator.isValid(30, "male", 178.0, 80.0, "bodybuilding", "lose_fat", "light"))
    }

    @Test
    fun tooYoungFails() {
        assertFalse(ProfileValidator.isValid(12, "male", 178.0, 80.0, "running", "maintain", "light"))
    }

    @Test
    fun missingFieldsFail() {
        assertFalse(ProfileValidator.isValid(30, null, 178.0, 80.0, "running", "maintain", "light"))
        assertFalse(ProfileValidator.isValid(30, "male", null, 80.0, "running", "maintain", "light"))
        assertFalse(ProfileValidator.isValid(30, "male", 178.0, 80.0, null, "maintain", "light"))
    }

    @Test
    fun outOfBoundsFail() {
        assertFalse(ProfileValidator.isValid(30, "male", 178.0, 500.0, "running", "maintain", "light"))
        assertFalse(ProfileValidator.isValid(30, "male", 90.0, 80.0, "running", "maintain", "light"))
    }
}
