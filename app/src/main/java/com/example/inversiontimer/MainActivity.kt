package com.example.inversiontimer

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.appcompat.app.AppCompatActivity
import com.example.inversiontimer.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnOverlayPermission.setOnClickListener { requestOverlayPermission() }
        binding.btnAccessibilityPermission.setOnClickListener { openAccessibilitySettings() }
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun refreshStatus() {
        val overlayOk = Settings.canDrawOverlays(this)
        val a11yOk = AccessibilityUtils.isServiceEnabled(this, AppMonitorService::class.java)
        val secureOk = SecureSettings.canWriteSecureSettings(this)

        binding.tvOverlayStatus.text =
            getString(if (overlayOk) R.string.status_granted else R.string.status_required)
        binding.tvAccessibilityStatus.text =
            getString(if (a11yOk) R.string.status_granted else R.string.status_required)
        binding.tvSecureStatus.text =
            getString(if (secureOk) R.string.status_granted else R.string.status_adb_required)
    }

    private fun requestOverlayPermission() {
        if (Settings.canDrawOverlays(this)) return
        val intent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:$packageName")
        )
        startActivity(intent)
    }

    private fun openAccessibilitySettings() {
        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
    }
}
