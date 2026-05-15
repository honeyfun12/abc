package com.example.inversiontimer

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.os.Build
import android.os.CountDownTimer
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.TextView

class OverlayManager(private val context: Context) {

    private val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private val main = Handler(Looper.getMainLooper())

    private var countdownView: View? = null
    private var countdownTimer: CountDownTimer? = null
    private var fallbackView: View? = null

    fun showCountdown(seconds: Int) = main.post {
        hideCountdownInternal()
        val view = LayoutInflater.from(context).inflate(R.layout.overlay_countdown, null, false)
        val title = view.findViewById<TextView>(R.id.tv_title)
        val number = view.findViewById<TextView>(R.id.tv_seconds)
        title.text = context.getString(R.string.countdown_title)
        number.text = seconds.toString()

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            overlayType(),
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON,
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.CENTER

        try {
            wm.addView(view, params)
            countdownView = view
        } catch (e: Exception) {
            return@post
        }

        countdownTimer = object : CountDownTimer(seconds * 1000L, 250L) {
            override fun onTick(msLeft: Long) {
                val s = ((msLeft + 999) / 1000).toInt().coerceAtLeast(0)
                number.text = s.toString()
            }
            override fun onFinish() {
                number.text = "0"
            }
        }.start()
    }

    fun showInversionFallback() = main.post {
        hideFallbackInternal()
        val view = View(context).apply {
            setBackgroundColor(Color.argb(110, 0, 0, 0))
            isClickable = false
            isFocusable = false
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            overlayType(),
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )
        try {
            wm.addView(view, params)
            fallbackView = view
        } catch (_: Exception) {}
    }

    fun hideAll() = main.post {
        hideCountdownInternal()
        hideFallbackInternal()
    }

    private fun hideCountdownInternal() {
        countdownTimer?.cancel()
        countdownTimer = null
        countdownView?.let { v ->
            try { wm.removeView(v) } catch (_: Exception) {}
        }
        countdownView = null
    }

    private fun hideFallbackInternal() {
        fallbackView?.let { v ->
            try { wm.removeView(v) } catch (_: Exception) {}
        }
        fallbackView = null
    }

    private fun overlayType(): Int = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
    } else {
        @Suppress("DEPRECATION")
        WindowManager.LayoutParams.TYPE_SYSTEM_ALERT
    }
}
