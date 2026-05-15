package com.example.inversiontimer

import android.accessibilityservice.AccessibilityService
import android.content.ComponentName
import android.content.Context
import android.provider.Settings

object AccessibilityUtils {

    fun isServiceEnabled(context: Context, serviceClass: Class<out AccessibilityService>): Boolean {
        val expected = ComponentName(context, serviceClass).flattenToString()
        val enabled = Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        return enabled.split(':').any { it.equals(expected, ignoreCase = true) }
    }
}
