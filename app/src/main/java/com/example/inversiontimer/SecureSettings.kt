package com.example.inversiontimer

import android.content.Context
import android.content.pm.PackageManager
import android.provider.Settings

object SecureSettings {

    private const val KEY_INVERSION = "accessibility_display_inversion_enabled"

    fun canWriteSecureSettings(context: Context): Boolean {
        return context.checkSelfPermission(android.Manifest.permission.WRITE_SECURE_SETTINGS) ==
            PackageManager.PERMISSION_GRANTED
    }

    fun setColorInversion(context: Context, enabled: Boolean): Boolean {
        if (!canWriteSecureSettings(context)) return false
        return try {
            Settings.Secure.putInt(context.contentResolver, KEY_INVERSION, if (enabled) 1 else 0)
            true
        } catch (_: SecurityException) {
            false
        }
    }

    fun isColorInversionOn(context: Context): Boolean {
        return try {
            Settings.Secure.getInt(context.contentResolver, KEY_INVERSION, 0) == 1
        } catch (_: Exception) {
            false
        }
    }
}
