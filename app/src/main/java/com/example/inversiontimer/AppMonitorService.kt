package com.example.inversiontimer

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent

class AppMonitorService : AccessibilityService() {

    private val handler = Handler(Looper.getMainLooper())
    private lateinit var overlayManager: OverlayManager

    private var state: State = State.Idle
    private var sessionPackage: String? = null

    private val endSessionRunnable = Runnable { endSession(goHome = true) }
    private val unlockRunnable = Runnable { unlockAndStartInversion() }

    private enum class State { Idle, Blocking, Active }

    override fun onServiceConnected() {
        super.onServiceConnected()
        overlayManager = OverlayManager(this)
        Log.i(TAG, "Service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        if (event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) return

        val pkg = event.packageName?.toString() ?: return
        if (pkg == packageName) return
        if (pkg.startsWith("com.android.systemui")) return

        val isTarget = pkg in TARGET_PACKAGES
        when (state) {
            State.Idle -> if (isTarget) startBlocking(pkg)
            State.Blocking -> if (!isTarget) cancelBlocking()
            State.Active -> if (!isTarget) endSession(goHome = false)
        }
    }

    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        if (::overlayManager.isInitialized) overlayManager.hideAll()
        SecureSettings.setColorInversion(this, false)
    }

    private fun startBlocking(pkg: String) {
        Log.i(TAG, "Start blocking for $pkg")
        state = State.Blocking
        sessionPackage = pkg
        overlayManager.showCountdown(BLOCK_SECONDS)
        handler.postDelayed(unlockRunnable, BLOCK_SECONDS * 1000L)
    }

    private fun cancelBlocking() {
        Log.i(TAG, "Cancel blocking")
        handler.removeCallbacks(unlockRunnable)
        overlayManager.hideAll()
        state = State.Idle
        sessionPackage = null
    }

    private fun unlockAndStartInversion() {
        Log.i(TAG, "Unlock + start inversion for $SESSION_SECONDS s")
        state = State.Active
        overlayManager.hideAll()
        val secureOk = SecureSettings.setColorInversion(this, true)
        if (!secureOk) overlayManager.showInversionFallback()
        handler.postDelayed(endSessionRunnable, SESSION_SECONDS * 1000L)
    }

    private fun endSession(goHome: Boolean) {
        Log.i(TAG, "End session, goHome=$goHome")
        handler.removeCallbacks(endSessionRunnable)
        handler.removeCallbacks(unlockRunnable)
        SecureSettings.setColorInversion(this, false)
        overlayManager.hideAll()
        state = State.Idle
        sessionPackage = null
        if (goHome) sendHome()
    }

    private fun sendHome() {
        val home = Intent(Intent.ACTION_MAIN).apply {
            addCategory(Intent.CATEGORY_HOME)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        startActivity(home)
    }

    companion object {
        private const val TAG = "AppMonitorService"
        private const val BLOCK_SECONDS = 10
        private const val SESSION_SECONDS = 5 * 60
        private val TARGET_PACKAGES = setOf(
            "com.google.android.youtube",
            "com.instagram.android"
        )
    }
}
