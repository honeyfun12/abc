package com.example.ibdcoach.data

enum class SessionType(val id: Int, val label: String, val defaultTime: String) {
    SESSION1(1, "아침 Core Finance/Valuation", "09:30"),
    SESSION2(2, "오후 BIWS Tech/기업분석", "14:30"),
    SESSION3(3, "저녁 UK IBD M&A/케이스", "20:30")
}

enum class Difficulty { EASY, NORMAL, HARD }

data class QuestionConfig(
    val includeEquityResearch: Boolean = true,
    val includePrivateEquity: Boolean = true,
    val targetMinutes: Int = 5,
    val questionsPerSession: Int = 1
)

data class DailyPerformance(
    val consecutiveHighDays: Int = 0,
    val consecutiveLowDays: Int = 0
)

data class FeedbackResult(
    val summary: String,
    val scoreLine: String,
    val structure: List<String>,
    val content: List<String>,
    val mistakes: List<String>,
    val oneLiner: String,
    val replayInstruction: String
)
